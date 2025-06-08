from rest_framework import serializers

class AlipayISVInitiateAuthSerializer(serializers.Serializer):
    # Identifies which entity (e.g., PaymentSubject or SigningCompany) is initiating auth.
    # The ID type depends on how you associate the app_auth_token.
    # Let's assume we are associating it with a PaymentSubject.
    payment_subject_id = serializers.IntegerField(required=True, help_text="ID of the PaymentSubject to authorize.")
    # Add any other parameters needed from the frontend to initiate auth.

class AlipayISVCallbackStateSerializer(serializers.Serializer):
    """
    Used to validate the 'state' parameter returned by Alipay.
    The 'state' should contain information to link the callback to the original request.
    This might involve decrypting or decoding the state parameter.
    For this example, let's assume state contains {'payment_subject_id': id}
    """
    payment_subject_id = serializers.IntegerField(required=True)
    # Add other fields that might have been encoded in the state string.

# Serializers for MerchantOnboardingViewSet actions
class MerchantOnboardingStartSerializer(serializers.Serializer):
    merchant_name = serializers.CharField(max_length=255, help_text="Name of the new merchant.")
    signing_company_id = serializers.IntegerField(help_text="ID of the SigningCompany for this merchant.")
    # Admin User details for the new merchant
    admin_email = serializers.EmailField(help_text="Email for the merchant's admin user.")
    admin_phone_number = serializers.CharField(max_length=20, help_text="Phone number for the merchant's admin user.")
    admin_password = serializers.CharField(write_only=True, help_text="Initial password for the merchant's admin user.")
    # Optional: admin_username if not derived from email/phone

class MerchantConfigurePaymentSubjectSerializer(serializers.Serializer):
    # merchant_id is passed in URL for detail action
    payment_channel_code = serializers.CharField(max_length=50, help_text="Code of the payment channel (e.g., ALIPAY_ISV).")
    # arrival_channel_code = serializers.CharField(max_length=50, required=False, help_text="Code of the arrival channel (if applicable).")

    # Payment Subject Info (some might be auto-filled or come from channel defaults)
    subject_name = serializers.CharField(max_length=200, help_text="Descriptive name for the payment subject.")
    # account_name = serializers.CharField(max_length=200, required=False, help_text="Account name (e.g., bank account holder name).")
    # account_number = serializers.CharField(max_length=100, required=False, help_text="Account number (sensitive, not typically set here directly).")
    # configs = serializers.JSONField(required=False, help_text="Initial basic configs, if any (sensitive parts handled by auth).")
    is_default = serializers.BooleanField(default=False, required=False, help_text="Set as default subject for this channel?")


# Serializer for UserVerificationView
class UserVerificationSerializer(serializers.Serializer):
    # user_id = serializers.IntegerField(required=False, help_text="User ID to verify. If not provided, request.user is used.")
    full_name = serializers.CharField(max_length=100, help_text="User's full legal name.")
    id_number = serializers.CharField(max_length=50, help_text="User's identification number (e.g., ID card).")
    # id_type = serializers.CharField(max_length=20, required=False, help_text="Type of ID, if multiple are supported.")
    # Add other fields like front/back ID card image paths if needed.

    def validate_id_number(self, value):
        # Basic validation for ID number length or format can go here.
        if len(value) < 5: # Arbitrary example
            raise serializers.ValidationError("ID number seems too short.")
        return value
