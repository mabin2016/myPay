from rest_framework import serializers
from .models import Account, Withdrawal, TransactionLedger, RechargeInvoice, ElectronicReceipt
from organizations.models import Merchant # Moved import to top
from organizations.serializers import MerchantSerializer
from payment_channels.serializers import PaymentSubjectSerializer
# settlements.serializers.PaymentOrderSerializer will be imported later when available.

class AccountSerializer(serializers.ModelSerializer):
    merchant_details = MerchantSerializer(source='merchant', read_only=True)
    payment_subject_details = PaymentSubjectSerializer(source='payment_subject', read_only=True)

    class Meta:
        model = Account
        fields = [
            'id', 'merchant', 'merchant_details',
            'payment_subject', 'payment_subject_details',
            'balance', 'available_balance', 'frozen_balance', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = (
            'id', 'created_at', 'updated_at',
            'merchant_details', 'payment_subject_details',
            'balance', 'available_balance', 'frozen_balance' # Typically modified by system logic
        )

class WithdrawalSerializer(serializers.ModelSerializer):
    account_details = AccountSerializer(source='account', read_only=True)
    # 'account' field for write operations (expects PK)
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())

    # target_account_number is an EncryptedField in the model.
    # It will be handled as a string by the serializer.

    class Meta:
        model = Withdrawal
        fields = [
            'id', 'account', 'account_details', 'amount', 'status',
            'target_account_name', 'target_account_number', 'bank_name',
            'remark', 'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'account_details', 'status', 'completed_at')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Withdrawal amount must be positive.")
        return value

class TransactionLedgerSerializer(serializers.ModelSerializer):
    account_details = AccountSerializer(source='account', read_only=True)
    # related_order_details: Placeholder until PaymentOrderSerializer is available
    # For now, just show the ID.
    related_order = serializers.PrimaryKeyRelatedField(read_only=True)
    # related_withdrawal_details: Placeholder, show ID.
    related_withdrawal = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TransactionLedger
        fields = [
            'id', 'account', 'account_details',
            'related_order',  # 'related_order_details', # Add when PaymentOrderSerializer is ready
            'related_withdrawal', # 'related_withdrawal_details', # Add when WithdrawalSerializer can be fully nested if needed
            'transaction_type', 'amount',
            'balance_before', 'balance_after',
            'available_balance_before', 'available_balance_after',
            'frozen_balance_before', 'frozen_balance_after',
            'remark', 'created_at' # updated_at is part of BaseModel but usually not relevant for append-only ledgers
        ]
        read_only_fields = '__all__' # Ledgers are typically append-only and system-generated.

class RechargeInvoiceSerializer(serializers.ModelSerializer):
    merchant_details = MerchantSerializer(source='merchant', read_only=True)
    # 'merchant' field for write operations (expects PK)
    merchant = serializers.PrimaryKeyRelatedField(queryset=Merchant.objects.all()) # Corrected queryset

    transaction_ledger_details = TransactionLedgerSerializer(source='transaction_ledger', read_only=True)
    # 'transaction_ledger' field for write operations (expects PK)
    transaction_ledger = serializers.PrimaryKeyRelatedField(queryset=TransactionLedger.objects.all())


    class Meta:
        model = RechargeInvoice
        fields = [
            'id', 'merchant', 'merchant_details',
            'transaction_ledger', 'transaction_ledger_details',
            'amount', 'invoice_type', 'title', 'tax_number', 'status',
            'invoice_number', 'invoice_code', # Added invoice_code
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at',
                            'merchant_details', 'transaction_ledger_details',
                            'status', 'invoice_number', 'invoice_code')

    def validate_transaction_ledger(self, value):
        if value.transaction_type != 1: # 1 for '充值' (Recharge)
            raise serializers.ValidationError("Invoice can only be requested for recharge transactions.")
        return value

class ElectronicReceiptSerializer(serializers.ModelSerializer):
    # payment_order_details: Placeholder until PaymentOrderSerializer is available
    payment_order = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ElectronicReceipt
        fields = [
            'id', 'payment_order', # 'payment_order_details', # Add when PaymentOrderSerializer is ready
            'receipt_file_url', 'generated_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at',
                            'receipt_file_url', 'generated_at')

# Serializer for the "Record Deposit" custom action on AccountViewSet
class RecordDepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    remark = serializers.CharField(max_length=255, allow_blank=True, required=False, help_text="Reason for the deposit or reference.")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Deposit amount must be positive.")
        return value
