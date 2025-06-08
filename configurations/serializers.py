from rest_framework import serializers
from .models import RiskControlConfig, WhitelistConfig, IpConfig

class RiskControlConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskControlConfig
        fields = ['id', 'name', 'config_type', 'rules', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_rules(self, value):
        # Example validation: Ensure 'rules' is a dictionary if a specific structure is expected.
        # This can be expanded based on the actual schema for different config_types.
        if not isinstance(value, dict):
            raise serializers.ValidationError("Rules must be a valid JSON object (dictionary).")

        # Example: if config_type == 1 (Amount Cap), rules might need 'max_amount_per_day'
        # config_type = self.initial_data.get('config_type') # Get config_type from incoming data
        # if config_type == 1: # Assuming 1 maps to '金额上限'
        #     if 'max_amount_per_day' not in value:
        #         raise serializers.ValidationError("For amount cap, 'max_amount_per_day' is required in rules.")
        #     if not isinstance(value['max_amount_per_day'], (int, float)) or value['max_amount_per_day'] < 0:
        #         raise serializers.ValidationError("'max_amount_per_day' must be a non-negative number.")
        return value

class WhitelistConfigSerializer(serializers.ModelSerializer):
    # id_number is an EncryptedField in the model.
    # The serializer will treat it as a string input/output.
    # Encryption/decryption is handled by the model field.
    # The model field was named 'value' in its definition.
    class Meta:
        model = WhitelistConfig
        fields = ['id', 'name', 'id_type', 'value', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ('id', 'created_at', 'updated_at')


class IpConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = IpConfig
        fields = ['id', 'ip_address', 'access_type', 'description', 'created_at', 'updated_at']
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_ip_address(self, value):
        # Django's GenericIPAddressField handles format validation at model level.
        # Additional custom validation can be added here if needed.
        return value
