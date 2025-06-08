from rest_framework import serializers
from .models import PaymentChannel, ArrivalChannel, PaymentSubject, OrderRule
from organizations.models import SigningCompany # Import the model for queryset
from organizations.serializers import SigningCompanySerializer # For nested representation

class PaymentChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentChannel
        fields = ['id', 'name', 'channel_code', 'is_active', 'config_details', 'created_at', 'updated_at']
        read_only_fields = ('id', 'created_at', 'updated_at')
        # For config_details (JSONField):
        # - If it contains sensitive data that should not be returned in GET,
        #   consider excluding it from 'fields' for GET or using different serializers for read/write.
        # - For now, it's included. If it were an EncryptedField, it would be handled by the field.

class ArrivalChannelSerializer(serializers.ModelSerializer):
    payment_channel_details = PaymentChannelSerializer(source='payment_channel', read_only=True)
    # 'payment_channel' field below will be used for write operations (expects PK)
    payment_channel = serializers.PrimaryKeyRelatedField(queryset=PaymentChannel.objects.all())


    class Meta:
        model = ArrivalChannel
        fields = [
            'id', 'payment_channel', 'payment_channel_details',
            'name', 'channel_code', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'payment_channel_details')

class PaymentSubjectSerializer(serializers.ModelSerializer):
    signing_company_details = SigningCompanySerializer(source='signing_company', read_only=True)
    payment_channel_details = PaymentChannelSerializer(source='payment_channel', read_only=True)

    # For write operations, expect PKs for foreign keys
    signing_company = serializers.PrimaryKeyRelatedField(queryset=SigningCompany.objects.all())
    payment_channel = serializers.PrimaryKeyRelatedField(queryset=PaymentChannel.objects.all())

    # account_number and configs are EncryptedFields in the model.
    # Serializer will treat them as regular text fields for input/output;
    # the encryption/decryption is handled by the model field itself.
    # No special serializer treatment is needed unless you want to make them write_only
    # or have other specific UI/validation needs beyond what TextField provides.

    class Meta:
        model = PaymentSubject
        fields = [
            'id', 'signing_company', 'signing_company_details',
            'payment_channel', 'payment_channel_details',
            'subject_name', 'account_name', 'account_number', # Will be string in/out
            'is_default', 'configs', # Will be JSON/dict in/out
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at',
                            'signing_company_details', 'payment_channel_details')

class OrderRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderRule
        fields = ['id', 'name', 'rule_type', 'config', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ('id', 'created_at', 'updated_at')
