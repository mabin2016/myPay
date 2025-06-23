from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import ALL views that are used either in urlpatterns directly or registered with the router
from .views import (
    PermissionViewSet, RoleViewSet, UserViewSet,
    AssignRolesToUserView, AssignPermissionsToRoleView,

    CompanyViewSet, GroupViewSet, EnterpriseViewSet, DataPermissionCollectionViewSet,
    UserCompanyAdminPermissionViewSet, UserGroupAdminPermissionViewSet, UserEnterpriseDataPermissionViewSet,

    UserDataPermissionConfigView, CheckDataPermissionView, EnterpriseOrdersView
)

router = DefaultRouter()

# Register RBAC Viewsets
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'users', UserViewSet, basename='user')

# Register Data Hierarchy & Permission Collection Viewsets
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'enterprises', EnterpriseViewSet, basename='enterprise')
router.register(r'data-permission-collections', DataPermissionCollectionViewSet, basename='datapermissioncollection')

# Register User-Specific Data Permission Viewsets (primarily for admin/debug)
router.register(r'user-company-admin-permissions', UserCompanyAdminPermissionViewSet, basename='usercompanyadminpermission')
router.register(r'user-group-admin-permissions', UserGroupAdminPermissionViewSet, basename='usergroupadminpermission')
router.register(r'user-enterprise-data-permissions', UserEnterpriseDataPermissionViewSet, basename='userenterprisedatapermission')

app_name = 'permissions_api_v1'

# Define urlpatterns, including router.urls and any custom paths
urlpatterns = [
    path('', include(router.urls)), # Include all registered ViewSet routes

    # Custom paths for specific actions
    path('assign-roles-to-user/', AssignRolesToUserView.as_view(), name='assign-roles-to-user'),
    path('assign-permissions-to-role/', AssignPermissionsToRoleView.as_view(), name='assign-permissions-to-role'),

    # Data Permission specific views
    path('configure-user-data-permissions/', UserDataPermissionConfigView.as_view(), name='configure-user-data-permissions'),
    path('check-data-permission/', CheckDataPermissionView.as_view(), name='check-data-permission'),

    # Example API with combined permissions
    path('enterprises/<int:enterprise_id>/orders/', EnterpriseOrdersView.as_view(), name='enterprise-orders'),
]
