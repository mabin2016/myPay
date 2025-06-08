from django.db import transaction, IntegrityError
from django.http import Http404
from django.contrib.auth import get_user_model
from rest_framework import viewsets, mixins, status, serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action

from core.permissions import IsAdminUserOrReadOnly
from core.responses import api_success_response, api_error_response, api_not_found_response
from .models import Account, Withdrawal, TransactionLedger, RechargeInvoice, ElectronicReceipt
from .serializers import (
    AccountSerializer,
    WithdrawalSerializer,
    TransactionLedgerSerializer,
    RechargeInvoiceSerializer,
    ElectronicReceiptSerializer,
    RecordDepositSerializer
)

User = get_user_model()

class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Account.objects.select_related('merchant', 'payment_subject').order_by('-created_at')
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Account.objects.none()
        if user.is_staff or user.is_superuser:
            return super().get_queryset()

        if hasattr(user, 'merchant') and user.merchant:
            return super().get_queryset().filter(merchant=user.merchant)
        elif hasattr(user, 'signing_company') and user.signing_company:
            return super().get_queryset().filter(merchant__signing_company=user.signing_company)

        return Account.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return api_success_response(
                data=paginated_response.data,
                message="Accounts listed.",
                count=paginated_response.data.get('count'),
                next=paginated_response.data.get('next'),
                previous=paginated_response.data.get('previous')
            )
        serializer = self.get_serializer(queryset, many=True)
        return api_success_response(data=serializer.data, message="Accounts listed.")

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Account not found or access denied.")
        serializer = self.get_serializer(instance)
        return api_success_response(data=serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser],
            serializer_class=RecordDepositSerializer, url_path='record-deposit', url_name='record_deposit')
    def record_deposit(self, request, pk=None):
        try:
            account = self.get_object()
        except Http404:
            return api_not_found_response(message="Account not found.")

        serializer = RecordDepositSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error_response(message="Invalid deposit data.", errors=serializer.errors)

        amount = serializer.validated_data['amount']
        remark = serializer.validated_data.get('remark', 'Admin deposit recorded.')

        try:
            with transaction.atomic():
                balance_before = account.balance
                available_balance_before = account.available_balance
                frozen_balance_before = account.frozen_balance

                account.balance += amount
                account.available_balance += amount
                account.save()

                TransactionLedger.objects.create(
                    account=account, transaction_type=1, amount=amount,
                    balance_before=balance_before, balance_after=account.balance,
                    available_balance_before=available_balance_before, available_balance_after=account.available_balance,
                    frozen_balance_before=frozen_balance_before, frozen_balance_after=account.frozen_balance,
                    remark=remark
                )
            account_serializer = AccountSerializer(account, context={'request': request})
            return api_success_response(data=account_serializer.data, message="Deposit recorded successfully.")
        except IntegrityError as e:
            return api_error_response(message=f"Database error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return api_error_response(message=f"An unexpected error occurred: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WithdrawalViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                        mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Withdrawal.objects.select_related('account__merchant').order_by('-created_at')
    serializer_class = WithdrawalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated: return Withdrawal.objects.none()
        if user.is_staff or user.is_superuser: return super().get_queryset()
        if hasattr(user, 'merchant') and user.merchant:
            return super().get_queryset().filter(account__merchant=user.merchant)
        elif hasattr(user, 'signing_company') and user.signing_company:
            return super().get_queryset().filter(account__merchant__signing_company=user.signing_company)
        return Withdrawal.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        account = serializer.validated_data['account']

        if not (user.is_staff or user.is_superuser):
            allowed_accounts_qs = Account.objects.none()
            if hasattr(user, 'merchant') and user.merchant:
                allowed_accounts_qs = Account.objects.filter(merchant=user.merchant, pk=account.pk)
            elif hasattr(user, 'signing_company') and user.signing_company:
                allowed_accounts_qs = Account.objects.filter(merchant__signing_company=user.signing_company, pk=account.pk)

            if not allowed_accounts_qs.exists():
                raise drf_serializers.ValidationError("You do not have permission to withdraw from this account.")

        if account.available_balance < serializer.validated_data['amount']:
            raise drf_serializers.ValidationError(f"Insufficient available balance. Available: {account.available_balance}")

        with transaction.atomic():
            account.available_balance -= serializer.validated_data['amount']
            account.frozen_balance += serializer.validated_data['amount']
            account.save()
            serializer.save(status=0)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                self.perform_create(serializer)
            except drf_serializers.ValidationError as e:
                return api_error_response(message="Withdrawal request failed.", errors=e.detail, status_code=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                 return api_error_response(message=f"An unexpected error occurred: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return api_success_response(data=serializer.data, message="Withdrawal request submitted.", status_code=status.HTTP_201_CREATED)
        return api_error_response(message="Invalid data for withdrawal request.", errors=serializer.errors)


class TransactionLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TransactionLedger.objects.select_related('account__merchant', 'related_order', 'related_withdrawal').order_by('-created_at')
    serializer_class = TransactionLedgerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated: return TransactionLedger.objects.none()
        if user.is_staff or user.is_superuser: return super().get_queryset()
        if hasattr(user, 'merchant') and user.merchant:
            return super().get_queryset().filter(account__merchant=user.merchant)
        elif hasattr(user, 'signing_company') and user.signing_company:
            return super().get_queryset().filter(account__merchant__signing_company=user.signing_company)
        return TransactionLedger.objects.none()


class RechargeInvoiceViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                             mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = RechargeInvoice.objects.select_related('merchant', 'transaction_ledger__account').order_by('-created_at')
    serializer_class = RechargeInvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated: return RechargeInvoice.objects.none()
        if user.is_staff or user.is_superuser: return super().get_queryset()
        if hasattr(user, 'merchant') and user.merchant:
            return super().get_queryset().filter(merchant=user.merchant)
        elif hasattr(user, 'signing_company') and user.signing_company:
             return super().get_queryset().filter(merchant__signing_company=user.signing_company)
        return RechargeInvoice.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        merchant = serializer.validated_data['merchant']

        if not (user.is_staff or user.is_superuser):
            is_owner = hasattr(user, 'merchant') and user.merchant == merchant
            is_in_company = hasattr(user, 'signing_company') and user.signing_company == merchant.signing_company
            if not (is_owner or is_in_company) :
                raise drf_serializers.ValidationError("You can only create invoices for your associated merchant.")

        serializer.save(status=0)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                self.perform_create(serializer)
            except drf_serializers.ValidationError as e:
                return api_error_response(message="Invoice request failed.", errors=e.detail, status_code=status.HTTP_400_BAD_REQUEST)
            return api_success_response(data=serializer.data, message="Recharge invoice request submitted.", status_code=status.HTTP_201_CREATED)
        return api_error_response(message="Invalid data for invoice request.", errors=serializer.errors)


class ElectronicReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ElectronicReceipt.objects.select_related('payment_order__merchant').order_by('-created_at')
    serializer_class = ElectronicReceiptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated: return ElectronicReceipt.objects.none()
        if user.is_staff or user.is_superuser: return super().get_queryset()
        if hasattr(user, 'merchant') and user.merchant:
            return super().get_queryset().filter(payment_order__merchant=user.merchant)
        elif hasattr(user, 'signing_company') and user.signing_company:
             return super().get_queryset().filter(payment_order__merchant__signing_company=user.signing_company)
        return ElectronicReceipt.objects.none()
