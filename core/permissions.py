from rest_framework import permissions

class IsSuperUserOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow superusers to edit an object.
    Read-only access is allowed for any request (authenticated or not).
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the superuser.
        return request.user and request.user.is_superuser

class IsObjectOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` or `user` attribute.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        # Try to get owner from 'owner' attribute, then 'user' attribute.
        object_owner = getattr(obj, 'owner', getattr(obj, 'user', None))
        return object_owner == request.user

class IsAdminUserOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access to any user, but write access only to admin users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff # is_staff is typically used for admin users

# Example of a role-based permission (conceptual, needs integration with User/Role models)
# class HasSalesRole(permissions.BasePermission):
#     """
#     Permission to check if the user has a 'Sales' role.
#     """
#     def has_permission(self, request, view):
#         if not request.user or not request.user.is_authenticated:
#             return False
#         # Assumes user has a method or attribute like `roles` that returns a list/queryset of Role objects
#         # And Role object has a `name` attribute.
#         try:
#             return request.user.user_roles.filter(name='Sales').exists() # Assuming UserRoleMap related_name is 'user_roles'
#         except AttributeError:
#             # Handle cases where user model might not have 'user_roles' or roles structure is different
#             # This could also involve checking user.groups if Django's Group model is used for roles.
#             return False

# class CanViewSensitiveData(permissions.BasePermission):
#     """
#     Custom permission for viewing sensitive data, potentially based on roles or specific flags.
#     """
#     def has_permission(self, request, view):
#         if not request.user or not request.user.is_authenticated:
#             return False
#         # Example: only users with 'manager' role or 'can_view_sensitive' permission flag
#         return (
#             hasattr(request.user, 'get_roles') and "manager" in request.user.get_roles() or
#             hasattr(request.user, 'has_perm') and request.user.has_perm('app_label.view_sensitive_data')
#         )
