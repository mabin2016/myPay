import logging
import json
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.conf import settings # Required for ALIPAY_ISV_CONFIG

from rest_framework.views import APIView
from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response as DRFResponse

from core.responses import api_success_response, api_error_response, api_not_found_response
from core.alipay_isv_service import generate_app_auth_url, exchange_auth_code_for_token
# from core.utils import encrypt_data, decrypt_data # If state needs encryption

from payment_channels.models import PaymentSubject, PaymentChannel
from organizations.models import Merchant, SigningCompany
from users.models import User as CustomUserModel # Direct import for adding fields if needed

from .serializers import (
    AlipayISVInitiateAuthSerializer,
    MerchantOnboardingStartSerializer,
    MerchantConfigurePaymentSubjectSerializer,
    UserVerificationSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)


class AlipayISVInitiateAuthView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = AlipayISVInitiateAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error_response(message="Invalid input.", errors=serializer.errors)

        payment_subject_id = serializer.validated_data['payment_subject_id']
        try:
            subject = PaymentSubject.objects.get(pk=payment_subject_id)
            if not (request.user.is_staff or
                    (hasattr(request.user, 'signing_company') and subject.signing_company == request.user.signing_company)):
                 return api_error_response("Forbidden: You cannot authorize this payment subject.", status_code=status.HTTP_403_FORBIDDEN)
        except PaymentSubject.DoesNotExist:
            return api_not_found_response(message="PaymentSubject not found.")

        state_data = {"payment_subject_id": payment_subject_id, "user_id": request.user.id, "domain": request.get_host()}
        state_param = json.dumps(state_data)

        # Use a more secure way to pass state in production (e.g., JWT, encrypted, or Redis-backed nonce)
        # For this example, plain JSON string is used. Ensure it's URL-safe.

        auth_url = generate_app_auth_url(state_param=state_param) # generate_app_auth_url should handle url encoding of state
        if auth_url:
            return api_success_response(data={"authorization_url": auth_url}, message="Redirect to Alipay for authorization.")
        else:
            return api_error_response(message="Failed to generate Alipay authorization URL.")


class AlipayISVAuthCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        auth_code = request.query_params.get('app_auth_code')
        state_param = request.query_params.get('state')

        if not auth_code: return api_error_response(message="Alipay callback error: 'app_auth_code' missing.")
        if not state_param: return api_error_response(message="Alipay callback error: 'state' parameter missing.")

        try:
            state_data = json.loads(state_param)
            payment_subject_id = state_data.get('payment_subject_id')
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in state parameter: {state_param}")
            return api_error_response(message="Invalid state parameter format.")
        if not payment_subject_id:
            return api_error_response(message="PaymentSubject ID not found in state.")

        token_info = exchange_auth_code_for_token(auth_code)
        if not token_info or 'app_auth_token' not in token_info:
            return api_error_response(message="Failed to exchange auth_code for app_auth_token.")

        try:
            subject = PaymentSubject.objects.get(pk=payment_subject_id)
            current_configs = subject.configs or {}
            current_configs['alipay_isv_app_auth_token'] = token_info['app_auth_token']
            current_configs['alipay_isv_app_refresh_token'] = token_info.get('app_refresh_token')
            current_configs['alipay_isv_user_id'] = token_info.get('alipay_user_id')
            current_configs['alipay_isv_auth_app_id'] = token_info.get('auth_app_id')
            current_configs['alipay_isv_token_expires_in'] = token_info.get('expires_in')

            subject.configs = current_configs
            subject.save()
            logger.info(f"Stored app_auth_token for PaymentSubject ID: {payment_subject_id}")
            # Ideally, redirect to a frontend page indicating success
            # For API, returning success is fine.
            return api_success_response(message="Alipay authorization successful.", data={"payment_subject_id": payment_subject_id})
        except PaymentSubject.DoesNotExist:
            return api_not_found_response(message="Associated PaymentSubject not found.")
        except Exception as e:
            logger.error(f"Error saving app_auth_token for PS ID {payment_subject_id}: {e}", exc_info=True)
            return api_error_response(message="Failed to store Alipay authorization token.")


class MerchantOnboardingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = drf_serializers.Serializer # Default dummy for router

    @action(detail=False, methods=['post'], url_path='start', serializer_class=MerchantOnboardingStartSerializer)
    def start_onboarding(self, request):
        serializer = MerchantOnboardingStartSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error_response(message="Invalid onboarding data.", errors=serializer.errors)

        data = serializer.validated_data
        try:
            signing_company = SigningCompany.objects.get(pk=data['signing_company_id'])
        except SigningCompany.DoesNotExist:
            return api_not_found_response(message="Specified SigningCompany not found.")

        try:
            with transaction.atomic():
                merchant_admin_username = data.get('admin_username', data['admin_phone_number'])
                if User.objects.filter(username=merchant_admin_username).exists():
                    return api_error_response(message=f"User with username '{merchant_admin_username}' already exists.")
                if User.objects.filter(email=data['admin_email']).exists():
                    return api_error_response(message=f"User with email '{data['admin_email']}' already exists.")
                if User.objects.filter(phone_number=data['admin_phone_number']).exists():
                     return api_error_response(message=f"User with phone_number '{data['admin_phone_number']}' already exists.")

                merchant_admin = User.objects.create_user(
                    phone_number=data['admin_phone_number'], email=data['admin_email'],
                    password=data['admin_password'], username=merchant_admin_username, status=1
                )
                # TODO: Assign 'Merchant Admin' role.

                merchant = Merchant.objects.create(
                    name=data['merchant_name'], signing_company=signing_company,
                    user=merchant_admin, status=1 # 1: "Info Collection" / "Awaiting Activation"
                )

            return api_success_response(
                data={"merchant_id": merchant.id, "user_id": merchant_admin.id, "merchant_code": merchant.merchant_code},
                message="Merchant onboarding started. Admin user and merchant record created.",
                status_code=status.HTTP_201_CREATED
            )
        except IntegrityError as e:
            logger.error(f"Onboarding integrity error: {e}", exc_info=True)
            return api_error_response(message=f"Data conflict: {str(e)}.")
        except Exception as e:
            logger.error(f"Error during merchant onboarding: {e}", exc_info=True)
            return api_error_response(message=f"Unexpected error: {str(e)}.")

    @action(detail=True, methods=['post'], url_path='configure-subject', serializer_class=MerchantConfigurePaymentSubjectSerializer)
    def configure_payment_subject(self, request, pk=None):
        try:
            merchant = Merchant.objects.get(pk=pk)
        except Merchant.DoesNotExist:
            return api_not_found_response(message="Merchant not found.")

        if not (request.user.is_staff or request.user == merchant.user):
             return api_error_response("Forbidden: You cannot configure this merchant.", status_code=status.HTTP_403_FORBIDDEN)

        serializer = MerchantConfigurePaymentSubjectSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error_response(message="Invalid data.", errors=serializer.errors)

        data = serializer.validated_data
        try:
            payment_channel = PaymentChannel.objects.get(channel_code=data['payment_channel_code'])
            subject, created = PaymentSubject.objects.update_or_create(
                signing_company=merchant.signing_company,
                payment_channel=payment_channel,
                subject_name=data['subject_name'],
                defaults={'is_default': data.get('is_default', False)}
            )

            response_data = {"payment_subject_id": subject.id, "subject_name": subject.subject_name}
            if payment_channel.channel_code == 'ALIPAY_ISV':
                response_data['next_step'] = "Proceed to Alipay ISV authorization for this payment subject."

            return api_success_response(data=response_data, message="Payment subject configured.")
        except PaymentChannel.DoesNotExist:
            return api_not_found_response(f"PaymentChannel '{data['payment_channel_code']}' not found.")
        except Exception as e:
            logger.error(f"Error configuring payment subject for merchant {pk}: {e}", exc_info=True)
            return api_error_response(f"An error occurred: {str(e)}.")

    @action(detail=True, methods=['post'], url_path='submit-approval')
    def submit_for_approval(self, request, pk=None):
        try:
            merchant = Merchant.objects.get(pk=pk)
        except Merchant.DoesNotExist:
            return api_not_found_response(message="Merchant not found.")

        if not (request.user.is_staff or request.user == merchant.user):
             return api_error_response("Forbidden.", status_code=status.HTTP_403_FORBIDDEN)

        if merchant.status == 1: # Example: 1 is "Info Collecting"
            merchant.status = 4 # Example: 4 is "Pending Approval"
            merchant.save(update_fields=['status', 'updated_at'])
            logger.info(f"Merchant {merchant.id} submitted for approval by {request.user.username}.")
            return api_success_response(message="Merchant submitted for approval.")
        else:
            return api_error_response(f"Cannot submit from current status: {merchant.get_status_display()}.")


class UserVerificationView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserVerificationSerializer

    def post(self, request, *args, **kwargs):
        serializer = UserVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error_response(message="Invalid verification data.", errors=serializer.errors)

        data = serializer.validated_data
        user_to_verify = request.user

        logger.info(f"Simulating User Verification for user: {user_to_verify.username}, "
                    f"Name: {data['full_name']}, ID Number: {data['id_number'][:4]}...")

        import random
        if random.choice([True, False]):
            if hasattr(user_to_verify, 'is_verified'): # Check if field exists
                user_to_verify.is_verified = True
                user_to_verify.save(update_fields=['is_verified', 'updated_at'])
            logger.info(f"Mock verification successful for user {user_to_verify.username}.")
            return api_success_response(message="User verification successful (mocked).", data={"is_verified": True})
        else:
            logger.info(f"Mock verification failed for user {user_to_verify.username}.")
            return api_error_response(message="User verification failed (mocked).", errors={"id_number": ["ID could not be verified."]})
