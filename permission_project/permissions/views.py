from django.contrib.auth.models import User
from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser # 使用Django Admin的权限作为基础API访问控制

from .models import Permission, Role
from .serializers import (
    PermissionSerializer, RoleSerializer, UserSerializer,
    UserRoleAssignmentSerializer, RolePermissionAssignmentSerializer
)

class PermissionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing page permissions.
    """
    queryset = Permission.objects.all().order_by('id')
    serializer_class = PermissionSerializer
    permission_classes = [IsAdminUser] # 仅管理员可管理权限定义

class RoleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing roles.
    """
    queryset = Role.objects.all().order_by('id')
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser] # 仅管理员可管理角色定义

    @action(detail=True, methods=['post'], serializer_class=RolePermissionAssignmentSerializer, url_path='assign-permissions')
    def assign_permissions(self, request, pk=None):
        """
        Assign permissions to a specific role.
        Expects a list of permission IDs.
        """
        role = self.get_object()
        serializer = RolePermissionAssignmentSerializer(data=request.data)
        if serializer.is_valid():
            permission_ids = serializer.validated_data['permission_ids']
            permissions = Permission.objects.filter(id__in=permission_ids)
            role.permissions.set(permissions)
            return Response({'status': 'permissions assigned'})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='get-permissions')
    def get_permissions(self, request, pk=None):
        """
        Get all permissions for a specific role.
        """
        role = self.get_object()
        permissions = role.permissions.all()
        serializer = PermissionSerializer(permissions, many=True)
        return Response(serializer.data)

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing users and their roles.
    This primarily uses Django's built-in User model.
    """
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser] # 仅管理员可管理用户

    @action(detail=True, methods=['post'], serializer_class=UserRoleAssignmentSerializer, url_path='assign-roles')
    def assign_roles(self, request, pk=None):
        """
        Assign roles to a specific user.
        Expects a list of role IDs.
        """
        user = self.get_object()
        serializer = UserRoleAssignmentSerializer(data=request.data)
        if serializer.is_valid():
            # user_id from serializer is validated but not strictly needed here as we use pk
            role_ids = serializer.validated_data['role_ids']
            roles = Role.objects.filter(id__in=role_ids)
            user.roles.set(roles)
            return Response({'status': 'roles assigned'})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='get-roles')
    def get_roles(self, request, pk=None):
        """
        Get all roles for a specific user.
        """
        user = self.get_object()
        roles = user.roles.all()
        serializer = RoleSerializer(roles, many=True) # Serialize the role objects
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='current-user-permissions')
    def current_user_permissions(self, request):
        """
        Get all permissions for the currently authenticated user.
        """
        user = request.user
        if user.is_anonymous:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

        if user.is_superuser: # 超级管理员拥有所有权限
            all_permissions = Permission.objects.all()
            serializer = PermissionSerializer(all_permissions, many=True)
            return Response(serializer.data)

        permission_codes = set()
        for role in user.roles.all():
            for perm in role.permissions.all():
                permission_codes.add(perm.code)

        # Fetch permission objects based on unique codes
        # This is just to return consistent Permission objects.
        # For actual checking, only codes might be enough.
        user_permissions = Permission.objects.filter(code__in=list(permission_codes))
        serializer = PermissionSerializer(user_permissions, many=True)
        return Response(serializer.data)


# It might be better to have separate, more focused views for assignment
# if ModelViewSet actions become too cluttered.
# For example:

class AssignRolesToUserView(generics.GenericAPIView):
    """
    Assign a list of roles to a user.
    """
    serializer_class = UserRoleAssignmentSerializer
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        role_ids = serializer.validated_data['role_ids']

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        roles = Role.objects.filter(id__in=role_ids)
        user.roles.set(roles) # .set() handles clearing old roles and adding new ones
        return Response({'status': f'Roles assigned to user {user.username}'}, status=status.HTTP_200_OK)

class AssignPermissionsToRoleView(generics.GenericAPIView):
    """
    Assign a list of permissions to a role.
    """
    serializer_class = RolePermissionAssignmentSerializer
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_id = serializer.validated_data['role_id']
        permission_ids = serializer.validated_data['permission_ids']

        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            return Response({"detail": "Role not found."}, status=status.HTTP_404_NOT_FOUND)

        permissions = Permission.objects.filter(id__in=permission_ids)
        role.permissions.set(permissions)
        return Response({'status': f'Permissions assigned to role {role.name}'}, status=status.HTTP_200_OK)

# --- Data Permission Views ---

from .models import (
    Company, Group, Enterprise, DataPermissionCollection,
    UserCompanyAdminPermission, UserGroupAdminPermission, UserEnterpriseDataPermission
)
from .serializers import (
    CompanySerializer, GroupSerializer, EnterpriseSerializer, DataPermissionCollectionSerializer,
    UserCompanyAdminPermissionSerializer, UserGroupAdminPermissionSerializer, UserEnterpriseDataPermissionSerializer,
    UserDataPermissionConfigSerializer
)
from django.db import transaction

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by('name')
    serializer_class = CompanySerializer
    permission_classes = [IsAdminUser] # Only admins can manage companies

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by('company__name', 'name')
    serializer_class = GroupSerializer
    permission_classes = [IsAdminUser] # Only admins can manage groups

class EnterpriseViewSet(viewsets.ModelViewSet):
    queryset = Enterprise.objects.all().order_by('group__company__name', 'group__name', 'name')
    serializer_class = EnterpriseSerializer
    permission_classes = [IsAdminUser] # Only admins can manage enterprises

class DataPermissionCollectionViewSet(viewsets.ModelViewSet):
    queryset = DataPermissionCollection.objects.all().order_by('name')
    serializer_class = DataPermissionCollectionSerializer
    permission_classes = [IsAdminUser] # Only admins can manage data permission collections


# Views for managing user-specific data permissions (mostly for admin/debug, main config via UserDataPermissionConfigView)

class UserCompanyAdminPermissionViewSet(viewsets.ModelViewSet):
    queryset = UserCompanyAdminPermission.objects.all()
    serializer_class = UserCompanyAdminPermissionSerializer
    permission_classes = [IsAdminUser]

class UserGroupAdminPermissionViewSet(viewsets.ModelViewSet):
    queryset = UserGroupAdminPermission.objects.all()
    serializer_class = UserGroupAdminPermissionSerializer
    permission_classes = [IsAdminUser]

class UserEnterpriseDataPermissionViewSet(viewsets.ModelViewSet):
    queryset = UserEnterpriseDataPermission.objects.all()
    serializer_class = UserEnterpriseDataPermissionSerializer
    permission_classes = [IsAdminUser]


class UserDataPermissionConfigView(generics.GenericAPIView):
    """
    API endpoint to configure all data permissions for a user.
    This single endpoint handles setting a user as:
    1. Company Admin (exclusive)
    2. Group Admin for multiple groups (exclusive of Company Admin)
    3. Specific enterprise permissions (exclusive of Company Admin or Admin of the enterprise's group)
    """
    serializer_class = UserDataPermissionConfigSerializer
    permission_classes = [IsAdminUser] # Only admins can configure user data permissions

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = data['user_id']
        user = User.objects.get(id=user_id)

        # Clear all existing data permissions for this user first
        UserCompanyAdminPermission.objects.filter(user=user).delete()
        UserGroupAdminPermission.objects.filter(user=user).delete()
        UserEnterpriseDataPermission.objects.filter(user=user).delete()

        if data['is_company_admin']:
            company_id = data['company_id']
            company = Company.objects.get(id=company_id)
            UserCompanyAdminPermission.objects.create(user=user, company=company)
            return Response({"status": f"User {user.username} configured as Company Admin for {company.name}."}, status=status.HTTP_200_OK)

        # If not company admin, process group admin and enterprise permissions
        for group_id in data.get('group_admin_for', []):
            group = Group.objects.get(id=group_id)
            UserGroupAdminPermission.objects.create(user=user, group=group)

        for ep_config in data.get('enterprise_permissions', []):
            enterprise_id = ep_config['enterprise_id']
            permission_codes = ep_config['permission_codes']

            enterprise = Enterprise.objects.get(id=enterprise_id)
            data_perms_qs = DataPermissionCollection.objects.filter(code__in=permission_codes)

            # Check if user is already admin of this enterprise's group
            if UserGroupAdminPermission.objects.filter(user=user, group=enterprise.group).exists():
                # This case should ideally be caught by serializer validation, but double check here.
                # If they are group admin, they shouldn't have specific enterprise perms for that group's enterprises.
                # Or, this means "admin" + "specific additional". The current logic is exclusive.
                continue

            uedp, created = UserEnterpriseDataPermission.objects.get_or_create(
                user=user,
                enterprise=enterprise
            )
            uedp.data_permissions.set(data_perms_qs)

        return Response({"status": f"Data permissions configured for user {user.username}."}, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        """
        Retrieve the current data permission configuration for a user.
        Expects 'user_id' as a query parameter.
        """
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({"detail": "user_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        config = {
            "user_id": user.id,
            "is_company_admin": False,
            "company_id": None,
            "group_admin_for": [],
            "enterprise_permissions": []
        }

        company_admin_perm = UserCompanyAdminPermission.objects.filter(user=user).first()
        if company_admin_perm:
            config["is_company_admin"] = True
            config["company_id"] = company_admin_perm.company_id
        else:
            group_admin_perms = UserGroupAdminPermission.objects.filter(user=user)
            config["group_admin_for"] = list(group_admin_perms.values_list('group_id', flat=True))

            enterprise_perms_qs = UserEnterpriseDataPermission.objects.filter(user=user).prefetch_related('data_permissions')

            # Exclude enterprises if their group is in group_admin_for, if that's the desired logic.
            # For now, showing all explicit enterprise perms.
            # group_admin_ids = set(config["group_admin_for"])

            for ep in enterprise_perms_qs:
                # if ep.enterprise.group_id in group_admin_ids:
                #     continue # Skip if user is admin of this enterprise's group
                config["enterprise_permissions"].append({
                    "enterprise_id": ep.enterprise_id,
                    "enterprise_name": ep.enterprise.name, # For easier display
                    "group_id": ep.enterprise.group_id,
                    "group_name": ep.enterprise.group.name,
                    "company_id": ep.enterprise.group.company_id,
                    "company_name": ep.enterprise.group.company.name,
                    "permission_codes": list(ep.data_permissions.values_list('code', flat=True)),
                    "permission_names": list(ep.data_permissions.values_list('name', flat=True)) # For easier display
                })

        return Response(config, status=status.HTTP_200_OK)


# Helper function / Service for checking data permission
# This will be the core logic used by API endpoints to guard resources.

def has_data_permission(user: User, enterprise_id: int, required_permission_codes: list[str]) -> bool:
    """
    Checks if a user has specific data permissions for a given enterprise.

    Args:
        user: The User object.
        enterprise_id: The ID of the target Enterprise.
        required_permission_codes: A list of data permission codes (e.g., ["business_data", "download_report"])
                                   The user must have ALL of these permissions.

    Returns:
        True if the user has the required permissions, False otherwise.
    """
    if not user.is_authenticated:
        return False

    # First, check if the enterprise exists. If not, permission is implicitly denied.
    try:
        enterprise = Enterprise.objects.select_related('group__company').get(id=enterprise_id)
    except Enterprise.DoesNotExist:
        return False

    # Superuser has all permissions for existing enterprises.
    if user.is_superuser:
        return True

    # 1. Check if user is Company Admin for the enterprise's company
    if UserCompanyAdminPermission.objects.filter(user=user, company=enterprise.group.company).exists():
        return True

    # 2. Check if user is Group Admin for the enterprise's group
    if UserGroupAdminPermission.objects.filter(user=user, group=enterprise.group).exists():
        return True

    # 3. Check for specific UserEnterpriseDataPermission
    try:
        user_enterprise_perm = UserEnterpriseDataPermission.objects.prefetch_related('data_permissions').get(
            user=user,
            enterprise=enterprise
        )

        assigned_codes = {perm.code for perm in user_enterprise_perm.data_permissions.all()}

        # Check if all required permission codes are present in the assigned codes
        if all(req_code in assigned_codes for req_code in required_permission_codes):
            return True

    except UserEnterpriseDataPermission.DoesNotExist:
        pass # No specific permission entry for this user and enterprise

    return False


class CheckDataPermissionView(generics.GenericAPIView):
    """
    An example view to demonstrate checking data permission.
    Query Params: user_id, enterprise_id, permission_codes (comma-separated)
    """
    permission_classes = [IsAdminUser] # Or IsAuthenticated for wider testing

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id')
        enterprise_id_str = request.query_params.get('enterprise_id')
        permission_codes_str = request.query_params.get('permission_codes')

        if not all([user_id, enterprise_id_str, permission_codes_str]):
            return Response(
                {"error": "user_id, enterprise_id, and permission_codes are required query parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=int(user_id))
            enterprise_id = int(enterprise_id_str)
        except (User.DoesNotExist, ValueError):
            return Response({"error": "Invalid user_id or enterprise_id."}, status=status.HTTP_400_BAD_REQUEST)

        required_codes = [code.strip() for code in permission_codes_str.split(',')]

        if not required_codes:
            return Response({"error": "permission_codes cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        has_perm = has_data_permission(user, enterprise_id, required_codes)

        return Response({
            "user_id": user.id,
            "enterprise_id": enterprise_id,
            "required_permission_codes": required_codes,
            "has_permission": has_perm
        })

# --- Example View with Combined Page and Data Permissions ---

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .permissions import HasPagePermission # Our RBAC page permission checker

class EnterpriseOrdersView(APIView):
    """
    Example API to get orders for a specific enterprise.
    Requires:
    1. Page Permission: 'view_orders'
    2. Data Permission: 'view_business_data' for the specified enterprise.
    """
    permission_classes = [IsAuthenticated, HasPagePermission]
    permission_codes = ['view_orders'] # Page permission code required

    def get(self, request, enterprise_id, *args, **kwargs):
        # enterprise_id would typically come from the URL pattern

        try:
            enterprise_id = int(enterprise_id)
            enterprise = Enterprise.objects.get(id=enterprise_id)
        except (ValueError, Enterprise.DoesNotExist):
            return Response({"error": "Invalid or non-existent enterprise_id."}, status=status.HTTP_404_NOT_FOUND)

        # Now, check data permission for this enterprise
        # The data permission code 'view_business_data' should be defined as a DataPermissionCollection instance.
        required_data_perm_codes = ["view_business_data"]

        if not has_data_permission(request.user, enterprise_id, required_data_perm_codes):
            return Response(
                {"error": f"You do not have '{', '.join(required_data_perm_codes)}' data permission for enterprise '{enterprise.name}' (ID: {enterprise_id})."},
                status=status.HTTP_403_FORBIDDEN
            )

        # If both page and data permissions are satisfied, proceed to fetch and return data.
        # This is a placeholder for actual order fetching logic.
        orders_data = [
            {"id": 1, "order_number": "ORD001", "amount": 100.50, "enterprise_id": enterprise_id},
            {"id": 2, "order_number": "ORD002", "amount": 75.20, "enterprise_id": enterprise_id},
        ]

        return Response({
            "message": f"Successfully fetched orders for enterprise '{enterprise.name}'. Page and data permissions verified.",
            "enterprise_id": enterprise_id,
            "orders": orders_data
        }, status=status.HTTP_200_OK)
