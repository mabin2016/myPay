from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Permission, Role

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'code', 'url', 'description', 'created_at', 'updated_at']

class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permission.objects.all(),
        help_text="权限ID列表"
    )

    class Meta:
        model = Role
        fields = ['id', 'name', 'permissions', 'description', 'created_at', 'updated_at']

class UserSerializer(serializers.ModelSerializer):
    roles = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Role.objects.all(),
        help_text="角色ID列表"
    )
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'roles', 'password']
        extra_kwargs = {
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def create(self, validated_data):
        roles_data = validated_data.pop('roles', [])
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        user.roles.set(roles_data)
        return user

    def update(self, instance, validated_data):
        roles_data = validated_data.pop('roles', None)
        password = validated_data.pop('password', None)

        instance = super().update(instance, validated_data)

        if password:
            instance.set_password(password)
            instance.save()

        if roles_data is not None:
            instance.roles.set(roles_data)
        return instance

class UserRoleAssignmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True
    )

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User with this ID does not exist.")
        return value

    def validate_role_ids(self, value):
        for role_id in value:
            if not Role.objects.filter(id=role_id).exists():
                raise serializers.ValidationError(f"Role with ID {role_id} does not exist.")
        return value

class RolePermissionAssignmentSerializer(serializers.Serializer):
    role_id = serializers.IntegerField()
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True
    )

    def validate_role_id(self, value):
        if not Role.objects.filter(id=value).exists():
            raise serializers.ValidationError("Role with this ID does not exist.")
        return value

    def validate_permission_ids(self, value):
        for perm_id in value:
            if not Permission.objects.filter(id=perm_id).exists():
                raise serializers.ValidationError(f"Permission with ID {perm_id} does not exist.")
        return value

# --- Data Permission Serializers ---

from .models import Company, Group, Enterprise, DataPermissionCollection, UserCompanyAdminPermission, UserGroupAdminPermission, UserEnterpriseDataPermission

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'created_at', 'updated_at']

class GroupSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField(source='company.id')
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'company_id', 'company_name', 'created_at', 'updated_at']

    def validate_company_id(self, value):
        if not Company.objects.filter(id=value).exists():
            raise serializers.ValidationError("Company with this ID does not exist.")
        return value

class EnterpriseSerializer(serializers.ModelSerializer):
    group_id = serializers.IntegerField(source='group.id')
    group_name = serializers.CharField(source='group.name', read_only=True)
    company_id = serializers.IntegerField(source='group.company.id', read_only=True)
    company_name = serializers.CharField(source='group.company.name', read_only=True)


    class Meta:
        model = Enterprise
        fields = ['id', 'name', 'group_id', 'group_name', 'company_id', 'company_name', 'created_at', 'updated_at']

    def validate_group_id(self, value):
        if not Group.objects.filter(id=value).exists():
            raise serializers.ValidationError("Group with this ID does not exist.")
        return value

class DataPermissionCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataPermissionCollection
        fields = ['id', 'name', 'code', 'description', 'created_at', 'updated_at']


class UserCompanyAdminPermissionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username', read_only=True)
    company_id = serializers.IntegerField(source='company.id')
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = UserCompanyAdminPermission
        fields = ['id', 'user_id', 'username', 'company_id', 'company_name', 'created_at']

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User with this ID does not exist.")
        return value

    def validate_company_id(self, value):
        if not Company.objects.filter(id=value).exists():
            raise serializers.ValidationError("Company with this ID does not exist.")
        return value

    def create(self, validated_data):
        # Ensure a user can only be an admin of one company via this specific table
        # Or remove other admin/granular permissions if this is set.
        # This logic might be better placed in a signal or view based on exact reqs.
        user_id = validated_data['user']['id']
        company_id = validated_data['company']['id']

        # Rule: "如果选择’签约公司管理员‘这个选项...就不能选择其他权限配置"
        # This implies if UserCompanyAdminPermission is created, other specific permissions should be cleared.
        UserGroupAdminPermission.objects.filter(user_id=user_id).delete()
        UserEnterpriseDataPermission.objects.filter(user_id=user_id).delete()

        # OneToOneField for user in UserCompanyAdminPermission model already ensures a user can have only one such entry.
        # If it was ForeignKey, we would do:
        # UserCompanyAdminPermission.objects.filter(user_id=user_id).delete()

        return super().create(validated_data)


class UserGroupAdminPermissionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username', read_only=True)
    group_id = serializers.IntegerField(source='group.id')
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = UserGroupAdminPermission
        fields = ['id', 'user_id', 'username', 'group_id', 'group_name', 'created_at']

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User with this ID does not exist.")
        return value

    def validate_group_id(self, value):
        if not Group.objects.filter(id=value).exists():
            raise serializers.ValidationError("Group with this ID does not exist.")
        return value

    def create(self, validated_data):
        # Rule: "如果不选择’签约公司管理员‘这个选项，则可以选择其他选项，’集团1管理员‘这个选项也类似。"
        # If a user is made Group Admin, they cannot be Company Admin.
        # And specific enterprise perms under this group might be implicitly granted or managed separately.
        user_id = validated_data['user']['id']
        if UserCompanyAdminPermission.objects.filter(user_id=user_id).exists():
            raise serializers.ValidationError("User is already a Company Admin and cannot be assigned as a Group Admin.")

        # If a user is made admin of Group X, clear any specific enterprise permissions
        # for enterprises under Group X for that user. This is one interpretation.
        # Another is that Group Admin implies all perms for all enterprises in that group.
        # The current design implies Group Admin is a separate flag, and specific perms are additive if not Company/Group admin.
        # For now, let's assume being a group admin doesn't auto-clear more granular perms unless specified.

        return super().create(validated_data)


class UserEnterpriseDataPermissionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username', read_only=True)
    enterprise_id = serializers.IntegerField(source='enterprise.id')
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)
    data_permissions = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=DataPermissionCollection.objects.all(),
        help_text="数据权限集合ID列表"
    )
    data_permission_details = DataPermissionCollectionSerializer(source='data_permissions', many=True, read_only=True)


    class Meta:
        model = UserEnterpriseDataPermission
        fields = [
            'id', 'user_id', 'username', 'enterprise_id', 'enterprise_name',
            'data_permissions', 'data_permission_details', 'created_at', 'updated_at'
        ]

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User with this ID does not exist.")
        return value

    def validate_enterprise_id(self, value):
        if not Enterprise.objects.filter(id=value).exists():
            raise serializers.ValidationError("Enterprise with this ID does not exist.")
        return value

    def create(self, validated_data):
        user_id = validated_data['user']['id']
        if UserCompanyAdminPermission.objects.filter(user_id=user_id).exists():
            raise serializers.ValidationError("User is a Company Admin and cannot be assigned granular enterprise permissions.")

        # Consider if user is a group admin for the enterprise's group
        enterprise_id = validated_data['enterprise']['id']
        enterprise = Enterprise.objects.get(id=enterprise_id)
        if UserGroupAdminPermission.objects.filter(user_id=user_id, group_id=enterprise.group_id).exists():
             raise serializers.ValidationError(f"User is an Admin for group '{enterprise.group.name}' and cannot be assigned granular permissions for enterprises within this group.")

        return super().create(validated_data)

    def update(self, instance, validated_data):
        user_id = validated_data.get('user', instance.user).id # Get user from validated_data or instance
        if UserCompanyAdminPermission.objects.filter(user_id=user_id).exists():
            raise serializers.ValidationError("User is a Company Admin and granular enterprise permissions cannot be modified.")

        enterprise_id = validated_data.get('enterprise', instance.enterprise).id
        enterprise = Enterprise.objects.get(id=enterprise_id)
        if UserGroupAdminPermission.objects.filter(user_id=user_id, group_id=enterprise.group_id).exists():
             raise serializers.ValidationError(f"User is an Admin for group '{enterprise.group.name}' and granular permissions for enterprises within this group cannot be modified.")

        return super().update(instance, validated_data)

# Serializer for the data permission configuration payload

class _EnterprisePermissionItemSerializer(serializers.Serializer): # Underscore to indicate internal use
    enterprise_id = serializers.IntegerField(required=True)
    permission_codes = serializers.ListField(child=serializers.CharField(), default=list)

class UserDataPermissionConfigSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    is_company_admin = serializers.BooleanField(default=False)
    company_id = serializers.IntegerField(required=False, allow_null=True) # Required if is_company_admin is True

    group_admin_for = serializers.ListField(
        child=serializers.IntegerField(), # List of Group IDs
        default=list,
        required=False
    )

    enterprise_permissions = serializers.ListField(
        child=_EnterprisePermissionItemSerializer(),
        default=list,
        required=False
    )

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User with this ID does not exist.")
        return value

    def validate_company_id(self, value):
        if value and not Company.objects.filter(id=value).exists():
            raise serializers.ValidationError("Company with this ID does not exist.")
        return value

    def validate(self, data):
        is_company_admin = data.get('is_company_admin')
        company_id = data.get('company_id')
        group_admin_for = data.get('group_admin_for', [])
        enterprise_permissions = data.get('enterprise_permissions', [])

        if is_company_admin:
            if not company_id:
                raise serializers.ValidationError({"company_id": "This field is required when is_company_admin is true."})
            if group_admin_for or enterprise_permissions:
                raise serializers.ValidationError("If user is a Company Admin, group admin settings and enterprise permissions must be empty.")

        # Validate group IDs in group_admin_for
        for group_id in group_admin_for:
            if not Group.objects.filter(id=group_id).exists():
                raise serializers.ValidationError(f"Group with ID {group_id} does not exist.")

        # Validate enterprise_permissions structure and IDs/codes
        for ep_entry in enterprise_permissions:
            if not isinstance(ep_entry, dict) or "enterprise_id" not in ep_entry or "permission_codes" not in ep_entry:
                raise serializers.ValidationError("Each entry in enterprise_permissions must be a dict with 'enterprise_id' and 'permission_codes'.")

            enterprise_id = ep_entry["enterprise_id"]
            if not Enterprise.objects.filter(id=enterprise_id).exists():
                raise serializers.ValidationError(f"Enterprise with ID {enterprise_id} does not exist.")

            permission_codes = ep_entry["permission_codes"]
            if not isinstance(permission_codes, list):
                raise serializers.ValidationError(f"permission_codes for enterprise {enterprise_id} must be a list.")

            for code in permission_codes:
                if not DataPermissionCollection.objects.filter(code=code).exists():
                    raise serializers.ValidationError(f"DataPermissionCollection with code '{code}' does not exist.")

            # Check if this enterprise belongs to a group where the user is already a group admin
            if group_admin_for:
                enterprise = Enterprise.objects.get(id=enterprise_id)
                if enterprise.group_id in group_admin_for:
                    raise serializers.ValidationError(f"Cannot set specific permissions for enterprise {enterprise_id} because user is already admin of its group ({enterprise.group.name}).")

        return data
