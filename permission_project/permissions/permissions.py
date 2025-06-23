from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class HasPagePermission(BasePermission):
    """
    Custom permission to check if a user has a specific page/API permission.
    This permission class is used by providing the required permission code(s)
    as a list to the `permission_codes` attribute on the view.

    Example usage in a view:
    ```
    class MyProtectedView(APIView):
        permission_classes = [IsAuthenticated, HasPagePermission]
        permission_codes = ['view_dashboard'] # or ['edit_settings', 'delete_user'] for multiple

        def get(self, request):
            # ... view logic ...
    ```
    """
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True # Superuser has all permissions

        # Get required permission codes from the view
        required_codes = getattr(view, 'permission_codes', None)
        if not required_codes:
            # If no permission_codes are specified on the view,
            # it's ambiguous. Deny access by default or log a warning.
            # For now, let's deny. For a less strict approach, one might return True.
            # print("Warning: No permission_codes defined on the view, access denied by default.")
            return False

        if isinstance(required_codes, str):
            required_codes = [required_codes]

        user_permissions = self._get_user_permission_codes(request.user)

        # Check if the user has ALL required permissions
        # To check if user has ANY of the permissions: use `any()`
        has_all_required = all(code in user_permissions for code in required_codes)

        if not has_all_required:
            # Construct a more specific message if needed
            missing_perms = [code for code in required_codes if code not in user_permissions]
            self.message = f"You are missing the following permissions: {', '.join(missing_perms)}"
            # Raising PermissionDenied here will use the DRF default renderer for the error.
            # If you just return False, the message attribute of the permission class is used.
            # For more control over the response, raise PermissionDenied directly.
            # raise PermissionDenied(detail=self.message)
            return False

        return True

    def _get_user_permission_codes(self, user):
        """
        Helper to get all permission codes for a user.
        """
        if not hasattr(user, '_permission_codes_cache'):
            codes = set()
            for role in user.roles.all().prefetch_related('permissions'):
                for perm in role.permissions.all():
                    codes.add(perm.code)
            user._permission_codes_cache = codes
        return user._permission_codes_cache

class HasPagePermissionOrReadOnly(HasPagePermission):
    """
    Allows read-only access (GET, HEAD, OPTIONS) even if specific permissions are not met,
    but requires permissions for write operations (POST, PUT, PATCH, DELETE).
    """
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True # Allow read-only methods for any authenticated user

        # For other methods, defer to the standard HasPagePermission check
        return super().has_permission(request, view)

# Example of how to get current user's permissions (already in UserViewSet)
# def get_current_user_permissions_list(user):
#     if user.is_anonymous:
#         return []
#     if user.is_superuser:
#         return list(Permission.objects.values_list('code', flat=True))

#     permission_codes = set()
#     for role in user.roles.all().prefetch_related('permissions'):
#         for perm in role.permissions.all():
#             permission_codes.add(perm.code)
#     return list(permission_codes)
