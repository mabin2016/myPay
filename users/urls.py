from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    UserRegistrationViewSet,
    UserViewSet,
    CustomTokenObtainPairView, # Use custom view
    RoleViewSet,
    PermissionViewSet,
    MenuViewSet,
    UserRoleMapViewSet,
    RolePermissionMapViewSet,
    RoleMenuMapViewSet
)

router = DefaultRouter()
router.register(r'register', UserRegistrationViewSet, basename='user-register') # For registration only
router.register(r'users', UserViewSet, basename='user') # For user CRUD by admin, and 'me' endpoint
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'menus', MenuViewSet, basename='menu')
router.register(r'user-roles', UserRoleMapViewSet, basename='user-role-map')
router.register(r'role-permissions', RolePermissionMapViewSet, basename='role-permission-map')
router.register(r'role-menus', RoleMenuMapViewSet, basename='role-menu-map')


# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),

    # JWT Token authentication
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]

# Example of how router generates URLs:
# /api/v1/users/ (list, create users - UserViewSet)
# /api/v1/users/{user_id}/ (retrieve, update, delete user - UserViewSet)
# /api/v1/users/me/ (current user details - UserViewSet custom action)
# /api/v1/users/register/ (user registration - UserRegistrationViewSet)
# /api/v1/users/roles/ (RoleViewSet)
# ... and so on for other viewsets.
