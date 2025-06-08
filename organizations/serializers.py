from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import SigningCompany, Group, Merchant, Platform
from users.serializers import UserSerializer # Ensure this is available and suitable

User = get_user_model()

class SigningCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = SigningCompany
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class MerchantSerializer(serializers.ModelSerializer):
    # Read-only nested serializers for displaying details
    # For write operations (create/update), the 'user', 'signing_company', 'group' fields
    # will expect PKs.
    user_details = UserSerializer(source='user', read_only=True)
    signing_company_details = SigningCompanySerializer(source='signing_company', read_only=True)
    group_details = GroupSerializer(source='group', read_only=True, allow_null=True)

    # Expose FK fields for write operations explicitly if needed, or rely on default
    # For example, 'user' field will expect a User PK for association.
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=False) # Set write_only=True if user_details is primary way to show user
    signing_company = serializers.PrimaryKeyRelatedField(queryset=SigningCompany.objects.all(), write_only=False)
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), allow_null=True, required=False, write_only=False)


    class Meta:
        model = Merchant
        fields = [
            'id', 'name', 'merchant_code',
            'signing_company', 'signing_company_details',
            'group', 'group_details',
            'user',  'user_details', # user_details for output, user (PK) for input
            'status', 'contract_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'merchant_code', 'created_at', 'updated_at',
                            'signing_company_details', 'group_details', 'user_details')
        # 'merchant_code' is often auto-generated on creation.

    def validate_merchant_code(self, value):
        # Example: If merchant_code is to be unique and manually set (though usually auto-generated)
        if self.instance is None and Merchant.objects.filter(merchant_code=value).exists(): # Check on create
            raise serializers.ValidationError("A merchant with this code already exists.")
        if self.instance and self.instance.merchant_code != value: # If trying to change it
             raise serializers.ValidationError("Merchant code cannot be changed after creation.")
        return value

    # If merchant_code is auto-generated in the model's save() method,
    # it should typically be read-only in the serializer.

class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# Serializer for the "UserSigningContract" custom action
class UserSigningContractSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(help_text="ID of the user to be associated with the signing company.")
    signing_company_id = serializers.IntegerField(help_text="ID of the signing company.")
    contract_details = serializers.CharField(allow_blank=True, required=False, style={'base_template': 'textarea.html'},
                                             help_text="Details of the contract or agreement.")

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User with this ID does not exist.")
        return value

    def validate_signing_company_id(self, value):
        if not SigningCompany.objects.filter(id=value).exists():
            raise serializers.ValidationError("Signing company with this ID does not exist.")
        return value

    # No .save() method here as it's not a ModelSerializer.
    # The view action will handle the logic.
