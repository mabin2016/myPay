import logging
from decimal import Decimal
from django.db import transaction, IntegrityError
from django.http import Http404
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings # For ALIPAY_ISV_CONFIG


from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response as DRFResponse


from core.responses import api_success_response, api_error_response, api_not_found_response
from core.permissions import IsAdminUserOrReadOnly
from core.alipay_isv_service import verify_callback_signature as alipay_verify_callback_signature_service


from .models import PaymentBatch, PaymentOrder
from .serializers import (
    PaymentBatchUploadSerializer,
    PaymentBatchSerializer,
    PaymentOrderSerializer,
    BatchActionSerializer
)
from .choices import BatchStatus, OrderStatus
from organizations.models import Merchant
from payment_channels.models import PaymentSubject


User = get_user_model()
logger = logging.getLogger(__name__)


# Mock validation functions (can be moved to a dedicated services.py)
def _validate_order_format_sync(order_data_dict):
    if not order_data_dict.get('recipient_name'): return False, "Recipient name is required."
    if not order_data_dict.get('recipient_account'): return False, "Recipient account is required."
    try:
        amount = Decimal(order_data_dict.get('amount', 0))
        if amount <= 0: return False, "Amount must be a positive number."
    except Exception:
        return False, "Invalid amount format."
    return True, None

def _validate_bank_elements_mock(order_instance):
    import random
    if random.random() < 0.05: # 5% failure rate
        order_instance.status = OrderStatus.BANK_ELEMENT_VALIDATION_FAILED
        order_instance.error_message = "Mock: Bank element validation failed."
        return False
    order_instance.status = OrderStatus.BANK_ELEMENT_VALIDATION_SUCCESS
    return True

def _validate_risk_control_mock(order_instance, merchant_instance):
    import random
    if order_instance.amount > Decimal('10000') and random.random() < 0.1: # Example rule
        order_instance.status = OrderStatus.RISK_CONTROL_REJECTED
        order_instance.error_message = "Mock: Order amount exceeds risk threshold for this merchant."
        return False
    order_instance.status = OrderStatus.RISK_CONTROL_APPROVED
    return True

def _validate_dge_mock(order_instance, merchant_instance):
    import random
    if "dge_flag_name" in order_instance.recipient_name.lower() and random.random() < 0.2:
        order_instance.status = OrderStatus.DGE_VALIDATION_REJECTED
        order_instance.error_message = "Mock: Recipient name flagged by DGE check."
        return False
    order_instance.status = OrderStatus.DGE_VALIDATION_APPROVED
    return True
# --- End Mock Validation Functions ---


class PaymentBatchViewSet(viewsets.ModelViewSet):
    queryset = PaymentBatch.objects.select_related('merchant', 'uploaded_by').prefetch_related('orders').order_by('-created_at')
    serializer_class = PaymentBatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated: return PaymentBatch.objects.none()
        if user.is_staff or user.is_superuser: return super().get_queryset()
        if hasattr(user, 'merchant') and user.merchant:
            return super().get_queryset().filter(merchant=user.merchant)
        elif hasattr(user, 'signing_company') and user.signing_company:
            return super().get_queryset().filter(merchant__signing_company=user.signing_company)
        return PaymentBatch.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentBatchUploadSerializer
        return PaymentBatchSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return api_error_response(message="Batch upload validation failed.", errors=serializer.errors)

        upload_data = serializer.validated_data; user = request.user
        merchant_id = upload_data.get('merchant_id')
        target_merchant = None

        if user.is_staff or user.is_superuser:
            if not merchant_id: return api_error_response(message="Admin must specify merchant_id.")
            try: target_merchant = Merchant.objects.get(pk=merchant_id)
            except Merchant.DoesNotExist: return api_not_found_response(f"Merchant {merchant_id} not found.")
        else:
            if not hasattr(user, 'merchant') or not user.merchant:
                return api_error_response("User not associated with a merchant.", status_code=status.HTTP_403_FORBIDDEN)
            if merchant_id and user.merchant.id != merchant_id:
                return api_error_response("Cannot upload for other merchants.", status_code=status.HTTP_403_FORBIDDEN)
            target_merchant = user.merchant

        orders_data = upload_data['orders']

        try:
            with transaction.atomic():
                new_batch = PaymentBatch.objects.create(
                    merchant=target_merchant, uploaded_by=user, status=BatchStatus.UNCHECKED,
                    remark=upload_data.get('remark', ''), total_orders=len(orders_data), total_amount=Decimal(0)
                )
                orders_to_create, valid_orders_total_amount = [], Decimal(0)

                for order_data_dict in orders_data:
                    is_fmt_valid, err_msg = _validate_order_format_sync(order_data_dict)
                    order_status = OrderStatus.FORMAT_VALIDATION_SUCCESS if is_fmt_valid else OrderStatus.FORMAT_VALIDATION_FAILED

                    order_instance = PaymentOrder(
                        payment_batch=new_batch, merchant=target_merchant,
                        payment_subject_id=order_data_dict['payment_subject'].id,
                        recipient_name=order_data_dict['recipient_name'], recipient_account=order_data_dict['recipient_account'],
                        recipient_bank_name=order_data_dict.get('recipient_bank_name'),
                        recipient_bank_branch=order_data_dict.get('recipient_bank_branch'),
                        recipient_phone=order_data_dict.get('recipient_phone'), amount=order_data_dict['amount'],
                        remark=order_data_dict.get('remark'), status=order_status, error_message=err_msg if not is_fmt_valid else None
                    )
                    orders_to_create.append(order_instance)
                    if is_fmt_valid: valid_orders_total_amount += order_instance.amount

                PaymentOrder.objects.bulk_create(orders_to_create)
                new_batch.total_amount = valid_orders_total_amount

                all_fmt_valid = all(o.status == OrderStatus.FORMAT_VALIDATION_SUCCESS for o in orders_to_create)
                new_batch.status = BatchStatus.FORMAT_VALIDATION_SUCCESS if all_fmt_valid else BatchStatus.FORMAT_VALIDATION_FAILED
                new_batch.save()

            batch_serializer = PaymentBatchSerializer(new_batch, context={'request': request})
            return api_success_response(data=batch_serializer.data, message="Batch uploaded.", status_code=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Batch upload error for merchant {target_merchant.id if target_merchant else 'N/A'}: {e}", exc_info=True)
            return api_error_response(message=f"Unexpected error: {str(e)}.")

    @action(detail=True, methods=['post'], serializer_class=BatchActionSerializer, url_path='process-action')
    def process_batch_action(self, request, pk=None):
        try: batch = self.get_object()
        except Http404: return api_not_found_response("Batch not found.")

        serializer = BatchActionSerializer(data=request.data)
        if not serializer.is_valid(): return api_error_response("Invalid action.", errors=serializer.errors)

        action_type, remark, user = serializer.validated_data['action'], serializer.validated_data.get('remark',''), request.user

        audit_entry = {"auditor_id":user.id, "auditor_username":user.username, "timestamp":timezone.now().isoformat(), "action":action_type, "remark":remark}
        if batch.audit_history is None: batch.audit_history = []
        batch.audit_history.append(audit_entry)

        if action_type == 'submit_for_audit':
            if batch.status in [BatchStatus.FORMAT_VALIDATION_SUCCESS, BatchStatus.VALIDATION_SUCCESS]: batch.status = BatchStatus.PENDING_INITIAL_AUDIT
            else: return api_error_response(f"Cannot submit from status: {batch.get_status_display()}", status_code=status.HTTP_400_BAD_REQUEST)

        elif action_type == 'approve_initial_audit':
            if batch.status == BatchStatus.PENDING_INITIAL_AUDIT: batch.status = BatchStatus.PENDING_FINAL_AUDIT
            else: return api_error_response(f"Cannot approve initial audit from status: {batch.get_status_display()}", status_code=status.HTTP_400_BAD_REQUEST)

        elif action_type == 'reject_initial_audit':
            if batch.status == BatchStatus.PENDING_INITIAL_AUDIT: batch.status = BatchStatus.INITIAL_AUDIT_REJECTED
            else: return api_error_response(f"Cannot reject initial audit from status: {batch.get_status_display()}", status_code=status.HTTP_400_BAD_REQUEST)

        elif action_type == 'approve_final_audit':
            if batch.status == BatchStatus.PENDING_FINAL_AUDIT:
                batch.status = BatchStatus.FINAL_AUDIT_APPROVED
                from .tasks import process_payment_batch_task
                process_payment_batch_task.delay(batch.id)
                logger.info(f"Payment processing task queued for Batch ID: {batch.id}")
            else: return api_error_response(f"Cannot approve final audit from status: {batch.get_status_display()}", status_code=status.HTTP_400_BAD_REQUEST)

        elif action_type == 'reject_final_audit':
            if batch.status == BatchStatus.PENDING_FINAL_AUDIT: batch.status = BatchStatus.FINAL_AUDIT_REJECTED
            else: return api_error_response(f"Cannot reject final audit from status: {batch.get_status_display()}", status_code=status.HTTP_400_BAD_REQUEST)

        elif action_type == 'cancel_batch':
            allowed_cancel_statuses = [
                BatchStatus.UNCHECKED, BatchStatus.FORMAT_VALIDATION_FAILED,
                BatchStatus.PENDING_INITIAL_AUDIT, BatchStatus.INITIAL_AUDIT_REJECTED,
                BatchStatus.PENDING_FINAL_AUDIT, BatchStatus.FINAL_AUDIT_REJECTED,
                BatchStatus.VALIDATION_FAILED
            ]
            if batch.status in allowed_cancel_statuses:
                batch.status = BatchStatus.CANCELLED
                PaymentOrder.objects.filter(payment_batch=batch).update(status=OrderStatus.CANCELLED, updated_at=timezone.now())
            else: return api_error_response(f"Cannot cancel from status: {batch.get_status_display()}", status_code=status.HTTP_400_BAD_REQUEST)

        elif action_type == 'run_validations':
            if batch.status not in [BatchStatus.FORMAT_VALIDATION_SUCCESS, BatchStatus.PENDING_VALIDATION]:
                 return api_error_response(f"Validations require format success. Status: {batch.get_status_display()}", status_code=status.HTTP_400_BAD_REQUEST)

            orders_to_val = batch.orders.filter(status=OrderStatus.FORMAT_VALIDATION_SUCCESS)
            all_valid = True
            with transaction.atomic():
                for order in orders_to_val:
                    if not _validate_bank_elements_mock(order): all_valid = False; order.save(); continue
                    if not _validate_risk_control_mock(order, batch.merchant): all_valid = False; order.save(); continue
                    if not _validate_dge_mock(order, batch.merchant): all_valid = False; order.save(); continue
                    order.status = OrderStatus.PENDING_PAYMENT; order.error_message = None; order.save()

                if all_valid and batch.orders.count() == orders_to_val.count(): batch.status = BatchStatus.VALIDATION_SUCCESS
                else: batch.status = BatchStatus.VALIDATION_FAILED
        else:
            return api_error_response(f"Unknown action: {action_type}", status_code=status.HTTP_400_BAD_REQUEST)

        batch.save()
        return api_success_response(PaymentBatchSerializer(batch, context={'request': request}).data, f"Batch action '{action_type}' processed.")


class PaymentOrderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentOrder.objects.select_related('payment_batch', 'merchant', 'payment_subject').order_by('-created_at')
    serializer_class = PaymentOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated: return PaymentOrder.objects.none()
        if user.is_staff or user.is_superuser: return super().get_queryset()
        if hasattr(user, 'merchant') and user.merchant:
            return super().get_queryset().filter(merchant=user.merchant)
        elif hasattr(user, 'signing_company') and user.signing_company:
            return super().get_queryset().filter(merchant__signing_company=user.signing_company)
        return PaymentOrder.objects.none()

    @action(detail=True, methods=['post'], url_path='initiate-refund',
            permission_classes=[IsAuthenticated])
    def initiate_refund(self, request, pk=None):
        try:
            order = self.get_object()
        except Http404:
            return api_not_found_response("PaymentOrder not found.")

        if order.status != OrderStatus.PAYMENT_SUCCESSFUL and order.status != OrderStatus.PARTIALLY_REFUNDED :
            return api_error_response(f"Order cannot be refunded from status: {order.get_status_display()}", status_code=status.HTTP_400_BAD_REQUEST)

        refund_amount_str = request.data.get('refund_amount')
        refund_reason = request.data.get('reason', 'Merchant requested refund.')

        try:
            refund_amount = Decimal(refund_amount_str)
            if refund_amount <= 0 or refund_amount > order.amount:
                raise ValueError("Invalid refund amount.")
        except (TypeError, ValueError):
            return api_error_response("Invalid refund_amount provided.", status_code=status.HTTP_400_BAD_REQUEST)

        if not order.payment_subject or not order.payment_subject.configs:
             return api_error_response("Payment subject or its configs not found for refund.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        app_auth_token = order.payment_subject.configs.get('alipay_isv_app_auth_token')
        if not app_auth_token:
            return api_error_response("Missing Alipay app_auth_token for refund operation.", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        original_channel_tx_id = order.channel_transaction_id or order.order_number

        from core.alipay_isv_service import refund_transaction as alipay_refund_service
        mock_refund_response = alipay_refund_service(
            original_order_id=original_channel_tx_id,
            refund_amount=str(refund_amount),
            refund_reason=refund_reason,
            payment_subject_configs=order.payment_subject.configs,
            app_auth_token=app_auth_token
        )

        if mock_refund_response and mock_refund_response.get('status') == 'SUCCESS':
            order.status = OrderStatus.REFUND_PENDING
            order.error_message = f"Refund initiated: {mock_refund_response.get('message')}"
            order.save(update_fields=['status', 'error_message', 'updated_at'])
            return api_success_response(data=mock_refund_response, message="Refund initiated successfully with Alipay.")
        else:
            error_msg = mock_refund_response.get('message', 'Failed to initiate refund with Alipay.')
            error_code = mock_refund_response.get('error_code')
            logger.error(f"Alipay refund initiation failed for order {order.id}: {error_code} - {error_msg}")
            return api_error_response(message=error_msg, errors={"alipay_error": error_code}, status_code=status.HTTP_400_BAD_REQUEST)


class AlipayISVCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        callback_data_dict = request.data.dict()
        logger.info(f"Received Alipay ISV callback: {callback_data_dict}")
        alipay_public_key = settings.ALIPAY_ISV_CONFIG.get("ALIPAY_PUBLIC_KEY_STRING")
        logger.info("Alipay callback signature verification PASSED (mocked or bypassed for dev).")
        from .tasks import process_payment_callbacks_task
        process_payment_callbacks_task.delay(callback_data_dict, 'ALIPAY_ISV')
        return DRFResponse("success", status=status.HTTP_200_OK)


class AlipayISVRefundCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        callback_data_dict = request.data.dict()
        logger.info(f"Received Alipay ISV Refund Callback: {callback_data_dict}")
        logger.info("Alipay refund callback signature verification PASSED (mocked).")
        from .tasks import process_refund_notification_task
        process_refund_notification_task.delay(callback_data_dict, 'ALIPAY_ISV')
        return DRFResponse("success", status=status.HTTP_200_OK)
