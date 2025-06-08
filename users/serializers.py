from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as BaseTokenObtainPairSerializer

from .models import Role, Permission, Menu, UserRoleMap, RolePermissionMap, RoleMenuMap
# Assuming EncryptedField will handle its own serialization/deserialization if used on a model field.
# If specific handling is needed in serializers for encrypted fields (e.g. write-only for input, always show masked),
# it would be done here. For now, we rely on the field's behavior.

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    # email = serializers.EmailField(required=True) # Assuming email is required
    # phone_number = serializers.CharField(required=True) # Assuming phone_number is required and unique

    class Meta:
        model = User
        fields = ('username', 'phone_number', 'email', 'password', 'password_confirm',
                  'first_name', 'last_name', 'signing_company') # Add other fields as needed for registration
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'signing_company': {'required': False}, # Adjust if these are mandatory during registration
            'username': {'required': True}, # Make username explicitly required if not covered by default
        }

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        # Add phone number format validation if not handled at model/db level, or use core.validators
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists(): # Case-insensitive check for email
            raise serializers.ValidationError("A user with this email address already exists.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Password fields didn't match."})
        # attrs.pop('password_confirm') # No longer needed after validation
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm') # Remove confirm password before creating user
        user = User.objects.create_user(**validated_data)
        # user.set_password(validated_data['password']) # create_user handles password hashing
        # user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    # For fields that might be encrypted (e.g., if you add a national_id with EncryptedField)
    # no special handling is needed here if EncryptedField works as expected.
    # If a field should be write-only for updates (like password):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'phone_number', 'email', 'first_name', 'last_name',
            'signing_company', 'status', 'is_active', 'is_staff', 'is_superuser',
            'last_login', 'date_joined', 'password' # Add password for updates
        )
        read_only_fields = ('last_login', 'date_joined', 'is_superuser', 'id')
        # Make some fields only modifiable by admins, or handle in view permissions.

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()
        return user


class CustomTokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['user_id'] = user.id
        token['username'] = user.username
        token['phone_number'] = user.phone_number
        # token['roles'] = [role.name for role in user.user_roles.all()] # Example if roles are set up
        # Be cautious about putting too much data in JWT.
        return token

    # Optional: Add custom fields to the response along with token
    # def validate(self, attrs):
    #     data = super().validate(attrs)
    #     data['user_id'] = self.user.id
    #     data['username'] = self.user.username
    #     return data


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at', 'id')


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission # Custom Permission model
        fields = ('id', 'name', 'codename', 'description', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at', 'id')


class MenuSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ('id', 'name', 'parent', 'url', 'icon', 'order', 'is_visible', 'children', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at', 'id')

    def get_children(self, obj):
        # Recursively serialize children
        children = Menu.objects.filter(parent=obj).order_by('order')
        if children.exists():
            return MenuSerializer(children, many=True, context=self.context).data
        return []

class UserRoleMapSerializer(serializers.ModelSerializer):
    # Optionally, include string representations or nested serializers for user and role
    # user_username = serializers.ReadOnlyField(source='user.username')
    # role_name = serializers.ReadOnlyField(source='role.name')

    class Meta:
        model = UserRoleMap
        fields = ('id', 'user', 'role') # 'user_username', 'role_name')
        # Use PrimaryKeyRelatedField for inputs, or nested serializers for outputs if desired.

class RolePermissionMapSerializer(serializers.ModelSerializer):
    # role_name = serializers.ReadOnlyField(source='role.name')
    # permission_codename = serializers.ReadOnlyField(source='permission.codename')
    class Meta:
        model = RolePermissionMap
        fields = ('id', 'role', 'permission')

class RoleMenuMapSerializer(serializers.ModelSerializer):
    # role_name = serializers.ReadOnlyField(source='role.name')
    # menu_name = serializers.ReadOnlyField(source='menu.name')
    class Meta:
        model = RoleMenuMap
        fields = ('id', 'role', 'menu')
