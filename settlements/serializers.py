from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import PaymentBatch, PaymentOrder
from organizations.models import Merchant # For validation
from organizations.serializers import MerchantSerializer # For nested display
from users.serializers import UserSerializer # For nested display
from payment_channels.models import PaymentSubject # For validation
# payment_channels.serializers.PaymentSubjectSerializer - for display (optional here)
# payment_channels.serializers.PaymentChannelSerializer - for display (optional here)
# payment_channels.serializers.ArrivalChannelSerializer - for display (optional here)
# payment_channels.serializers.OrderRuleSerializer - for display (optional here)

User = get_user_model()

class PaymentOrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating individual payment orders within a batch.
    """
    # payment_subject is expected as PrimaryKeyRelatedField by default from ModelSerializer
    # if you need to customize, define explicitly:
    payment_subject = serializers.PrimaryKeyRelatedField(
        queryset=PaymentSubject.objects.all(),
        help_text="ID of the PaymentSubject to be used for this order."
    )
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)

    class Meta:
        model = PaymentOrder
        fields = [
            'payment_subject', 'recipient_name', 'recipient_account',
            'recipient_bank_name', 'recipient_bank_branch', 'recipient_phone',
            'amount', 'remark'
        ]
        # Fields like order_number, payment_batch, status, merchant are set by the system during batch creation.

    def validate_recipient_phone(self, value):
        # Basic phone validation, can be enhanced using core.validators
        if value and not value.isdigit() or (len(value) < 7 or len(value) > 15): # Simplified example
            raise serializers.ValidationError("Invalid phone number format.")
        return value


class PaymentBatchUploadSerializer(serializers.Serializer):
    merchant_id = serializers.IntegerField(required=False, help_text="ID of the merchant this batch belongs to. If not provided, taken from authenticated user if applicable.")
    orders = PaymentOrderCreateSerializer(many=True, max_length=4000) # Max 4000 orders per batch
    remark = serializers.CharField(required=False, allow_blank=True, style={'base_template': 'textarea.html'})

    def validate_merchant_id(self, value):
        if not Merchant.objects.filter(pk=value).exists():
            raise serializers.ValidationError(f"Merchant with ID {value} does not exist.")
        return value

    def validate_orders(self, value):
        if not value:
            raise serializers.ValidationError("Orders list cannot be empty.")
        if len(value) > 4000: # Redundant due to max_length but good for explicit error
            raise serializers.ValidationError("A single batch cannot exceed 4000 orders.")
        return value


class PaymentOrderSerializer(serializers.ModelSerializer):
    # Using PrimaryKeyRelatedField for related objects to keep it simple for now.
    # Replace with specific serializers for detailed nested representation if needed.
    payment_batch = serializers.PrimaryKeyRelatedField(read_only=True)
    merchant = serializers.PrimaryKeyRelatedField(read_only=True) # Or MerchantSerializer(read_only=True)
    payment_subject = serializers.PrimaryKeyRelatedField(read_only=True) # Or PaymentSubjectSerializer(read_only=True)
    payment_channel_used = serializers.PrimaryKeyRelatedField(read_only=True)
    arrival_channel_used = serializers.PrimaryKeyRelatedField(read_only=True)
    applied_rule = serializers.PrimaryKeyRelatedField(read_only=True)

    # To show names/codes instead of just PKs without full nested serializers:
    # merchant_name = serializers.CharField(source='merchant.name', read_only=True)
    # payment_subject_name = serializers.CharField(source='payment_subject.subject_name', read_only=True)

    class Meta:
        model = PaymentOrder
        fields = '__all__' # Includes all fields from the PaymentOrder model
        read_only_fields = ('order_number', 'status', 'error_message', 'created_at', 'updated_at')


class PaymentBatchSerializer(serializers.ModelSerializer):
    orders = PaymentOrderSerializer(many=True, read_only=True) # Display orders within the batch
    merchant_details = MerchantSerializer(source='merchant', read_only=True)
    uploaded_by_details = UserSerializer(source='uploaded_by', read_only=True)

    # For write operations on merchant/uploaded_by, if allowed directly (usually not for updates)
    merchant = serializers.PrimaryKeyRelatedField(queryset=Merchant.objects.all(), write_only=True, required=False)
    uploaded_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True, required=False)


    class Meta:
        model = PaymentBatch
        fields = [
            'id', 'batch_number', 'merchant', 'merchant_details',
            'uploaded_by', 'uploaded_by_details',
            'total_orders', 'total_amount', 'status', 'remark',
            'audit_history', 'orders', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'batch_number', 'total_orders', 'total_amount',
                            'audit_history', 'created_at', 'updated_at',
                            'merchant_details', 'uploaded_by_details', 'orders')
        # Status is typically managed by actions, not direct PATCH, but can be made writable for admins if needed.

class BatchActionSerializer(serializers.Serializer): # Renamed from BatchAuditActionSerializer for broader use
    ACTION_CHOICES = [
        ('submit_for_audit', 'Submit for Audit'),
        ('approve_initial_audit', 'Approve Initial Audit'),
        ('reject_initial_audit', 'Reject Initial Audit'),
        ('approve_final_audit', 'Approve Final Audit'),
        ('reject_final_audit', 'Reject Final Audit'),
        ('cancel_batch', 'Cancel Batch'),
        ('run_validations', 'Run Validations') # For the placeholder validation action
    ]
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    remark = serializers.CharField(required=False, allow_blank=True, style={'base_template': 'textarea.html'})
    # auditor_id will be taken from request.user

    def validate_action(self, value):
        # Specific validation based on action can be added here or in the view.
        return value
