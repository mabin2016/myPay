from django.contrib.auth.models import User, Group as DjangoGroup # Django's own Group, not our permission Group model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import (
    Permission, Role,
    Company, Group as PermissionGroup, Enterprise, DataPermissionCollection, # Our Group model is PermissionGroup
    UserCompanyAdminPermission, UserGroupAdminPermission, UserEnterpriseDataPermission
)
from .permissions import HasPagePermission
from .views import has_data_permission, EnterpriseOrdersView # For direct testing of view permission and helper

# Helper to create a mock request for permission classes
from django.http import HttpRequest
from rest_framework.views import APIView


class MockRequest:
    def __init__(self, user=None, method='GET'):
        self.user = user
        self.method = method

class MockView(APIView): # Inherit from APIView to be a valid view for DRF permissions
    permission_codes = []


class RBACPermissionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.staff_user = User.objects.create_user(username='staffuser', password='password123', is_staff=True) # For IsAdminUser tests
        self.superuser = User.objects.create_superuser(username='superuser', password='password123', email='super@example.com')

        self.perm1 = Permission.objects.create(name='View Dashboard', code='view_dashboard')
        self.perm2 = Permission.objects.create(name='Edit Settings', code='edit_settings')

        self.role1 = Role.objects.create(name='Viewer')
        self.role1.permissions.add(self.perm1)

        self.role2 = Role.objects.create(name='Editor')
        self.role2.permissions.add(self.perm1, self.perm2)

        self.user.roles.add(self.role1)

    def test_has_page_permission_granted(self):
        permission_checker = HasPagePermission()
        request = MockRequest(user=self.user)
        view = MockView()
        view.permission_codes = ['view_dashboard']

        self.assertTrue(permission_checker.has_permission(request, view))

    def test_has_page_permission_denied(self):
        permission_checker = HasPagePermission()
        request = MockRequest(user=self.user)
        view = MockView()
        view.permission_codes = ['edit_settings'] # User only has 'view_dashboard'

        self.assertFalse(permission_checker.has_permission(request, view))
        self.assertIn("edit_settings", permission_checker.message)


    def test_has_page_permission_superuser(self):
        permission_checker = HasPagePermission()
        request = MockRequest(user=self.superuser)
        view = MockView()
        view.permission_codes = ['any_permission_code'] # Superuser should bypass specific codes

        self.assertTrue(permission_checker.has_permission(request, view))

    def test_has_page_permission_no_codes_on_view_denied(self):
        permission_checker = HasPagePermission()
        request = MockRequest(user=self.user)
        view = MockView()
        view.permission_codes = [] # Or attribute not set - default behavior is to deny

        # Our implementation currently denies if no permission_codes are set on the view
        self.assertFalse(permission_checker.has_permission(request, view))

    def test_enterprise_orders_view_page_permission(self):
        # Test the page permission part of EnterpriseOrdersView
        # This test does not set up data permissions, so it might fail on the data perm check if page perm passes.
        # We're mostly interested if the HasPagePermission part works via the view's setup.

        # User without 'view_orders' permission
        client = APIClient()
        client.force_authenticate(user=self.user) # self.user has 'view_dashboard' but not 'view_orders'

        # Create a dummy enterprise for the URL
        company = Company.objects.create(name="Test Corp")
        group = PermissionGroup.objects.create(name="Test Group", company=company)
        enterprise = Enterprise.objects.create(name="Test Ent", group=group)

        # Create the 'view_orders' page permission
        Permission.objects.create(name="View Orders", code="view_orders")
        # 'view_business_data' DataPermissionCollection also needs to exist for the full view logic
        DataPermissionCollection.objects.create(name="View Business Data", code="view_business_data")


        url = reverse('permissions_api_v1:enterprise-orders', kwargs={'enterprise_id': enterprise.id})
        response = client.get(url)
        # Expect 403 because HasPagePermission should deny due to missing 'view_orders'
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("view_orders", response.data.get("detail", response.data.get("error", ""))) # Check message

        # User with 'view_orders' permission
        view_orders_perm = Permission.objects.get(code='view_orders')
        role = self.user.roles.first()
        if not role: # Should exist from setUp, but defensive
            role = Role.objects.create(name="Temp Role Test")
            self.user.roles.add(role)
        role.permissions.add(view_orders_perm)

        # Clear the cache on the user object if it exists, because we modified permissions
        if hasattr(self.user, '_permission_codes_cache'):
            delattr(self.user, '_permission_codes_cache')

        client.force_authenticate(user=self.user) # User should now have 'view_orders'
        response = client.get(url)

        # Now, page permission should pass. The view will then do its data permission check.
        # If data permission is NOT set up for self.user on this enterprise, it will also be 403.
        # This is fine, it means page permission passed.
        # The error message will be from the data permission check.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        expected_error_message_part = "view_business_data"
        actual_error_message = ""

        if isinstance(response.data, dict) and "error" in response.data:
            actual_error_message = response.data["error"]
        else:
            actual_error_message = str(response.data)
            # print(f"DEBUG: Unexpected response.data structure in test_enterprise_orders_view_page_permission: {actual_error_message}")
            # This will help see what the response actually is if it's not {"error": "..."}

        self.assertIn(expected_error_message_part, actual_error_message)


class DataPermissionLogicTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='datapermuser1', password='password123')
        self.user2 = User.objects.create_user(username='datapermuser2', password='password123')
        self.company_admin_user = User.objects.create_user(username='compadmin', password='password123')
        self.group_admin_user = User.objects.create_user(username='groupadmin', password='password123')
        self.superuser = User.objects.create_superuser(username='data_superuser', password='password123')

        self.company = Company.objects.create(name="DataTest Company")
        self.group1 = PermissionGroup.objects.create(name="DataTest Group 1", company=self.company)
        self.enterprise1_1 = Enterprise.objects.create(name="DataTest Enterprise 1.1", group=self.group1)
        self.enterprise1_2 = Enterprise.objects.create(name="DataTest Enterprise 1.2", group=self.group1)

        self.group2 = PermissionGroup.objects.create(name="DataTest Group 2", company=self.company)
        self.enterprise2_1 = Enterprise.objects.create(name="DataTest Enterprise 2.1", group=self.group2)

        self.dp_view_biz = DataPermissionCollection.objects.create(name="View Business Data", code="view_business_data")
        self.dp_edit_biz = DataPermissionCollection.objects.create(name="Edit Business Data", code="edit_business_data")
        self.dp_audit = DataPermissionCollection.objects.create(name="Audit Data", code="audit_data")

        # User1: Specific permission for enterprise1_1
        uedp1 = UserEnterpriseDataPermission.objects.create(user=self.user1, enterprise=self.enterprise1_1)
        uedp1.data_permissions.add(self.dp_view_biz, self.dp_edit_biz)

        # Company Admin User: Admin for self.company
        UserCompanyAdminPermission.objects.create(user=self.company_admin_user, company=self.company)

        # Group Admin User: Admin for self.group1
        UserGroupAdminPermission.objects.create(user=self.group_admin_user, group=self.group1)

        self.client = APIClient() # For UserDataPermissionConfigView tests

    def test_has_data_permission_specific_grant(self):
        self.assertTrue(has_data_permission(self.user1, self.enterprise1_1.id, ["view_business_data"]))
        self.assertTrue(has_data_permission(self.user1, self.enterprise1_1.id, ["edit_business_data"]))
        self.assertTrue(has_data_permission(self.user1, self.enterprise1_1.id, ["view_business_data", "edit_business_data"]))

    def test_has_data_permission_specific_denied(self):
        self.assertFalse(has_data_permission(self.user1, self.enterprise1_1.id, ["audit_data"])) # Not granted
        self.assertFalse(has_data_permission(self.user1, self.enterprise1_2.id, ["view_business_data"])) # Granted for 1.1, not 1.2
        self.assertFalse(has_data_permission(self.user2, self.enterprise1_1.id, ["view_business_data"])) # User2 has no grants

    def test_has_data_permission_company_admin(self):
        # Company admin should have all permissions for all enterprises in their company
        self.assertTrue(has_data_permission(self.company_admin_user, self.enterprise1_1.id, ["view_business_data"]))
        self.assertTrue(has_data_permission(self.company_admin_user, self.enterprise1_1.id, ["audit_data"])) # Even if not explicitly defined
        self.assertTrue(has_data_permission(self.company_admin_user, self.enterprise2_1.id, ["any_perm_code"]))

    def test_has_data_permission_group_admin(self):
        # Group admin for group1 should have all perms for enterprises in group1
        self.assertTrue(has_data_permission(self.group_admin_user, self.enterprise1_1.id, ["view_business_data"]))
        self.assertTrue(has_data_permission(self.group_admin_user, self.enterprise1_2.id, ["audit_data"]))
        # Group admin for group1 should NOT have perms for enterprises in group2 by virtue of group1 adminship
        self.assertFalse(has_data_permission(self.group_admin_user, self.enterprise2_1.id, ["view_business_data"]))

    def test_has_data_permission_superuser(self):
        self.assertTrue(has_data_permission(self.superuser, self.enterprise1_1.id, ["any_code_whatsoever"]))
        non_existent_enterprise_id = 9999
        self.assertFalse(has_data_permission(self.superuser, non_existent_enterprise_id, ["any_code"])) # False because enterprise doesn't exist

    def test_has_data_permission_non_existent_enterprise(self):
        self.assertFalse(has_data_permission(self.user1, 9999, ["view_business_data"]))

    def test_data_permission_hierarchy(self):
        # User1 has specific for E1.1. GroupAdmin has for G1. CompanyAdmin has for Company.
        # Grant specific to User1 for E1.1
        uedp_user1_e1_1 = UserEnterpriseDataPermission.objects.get(user=self.user1, enterprise=self.enterprise1_1)
        uedp_user1_e1_1.data_permissions.set([self.dp_view_biz])

        # Test User1: has view on E1.1, not audit
        self.assertTrue(has_data_permission(self.user1, self.enterprise1_1.id, ["view_business_data"]))
        self.assertFalse(has_data_permission(self.user1, self.enterprise1_1.id, ["audit_data"]))

        # Test GroupAdmin: should have audit on E1.1 (and any other perm)
        self.assertTrue(has_data_permission(self.group_admin_user, self.enterprise1_1.id, ["audit_data"]))
        self.assertTrue(has_data_permission(self.group_admin_user, self.enterprise1_1.id, ["view_business_data"])) # Also this

        # Test CompanyAdmin: should have audit on E1.1
        self.assertTrue(has_data_permission(self.company_admin_user, self.enterprise1_1.id, ["audit_data"]))


class UserDataPermissionConfigViewTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='configadmin', password='password123')
        self.test_user = User.objects.create_user(username='subjectuser', password='password123')

        self.company1 = Company.objects.create(name="Config Company 1")
        self.group1_1 = PermissionGroup.objects.create(name="Config Group 1.1", company=self.company1)
        self.enterprise1_1_1 = Enterprise.objects.create(name="Config Ent 1.1.1", group=self.group1_1)
        self.dp_biz = DataPermissionCollection.objects.create(code="biz_data_cfg", name="Business Data CFG")
        self.dp_fin = DataPermissionCollection.objects.create(code="fin_data_cfg", name="Financial Data CFG")

        self.url = reverse('permissions_api_v1:configure-user-data-permissions')
        self.client.force_authenticate(user=self.admin_user)

    def test_configure_as_company_admin(self):
        payload = {
            "user_id": self.test_user.id,
            "is_company_admin": True,
            "company_id": self.company1.id,
            "group_admin_for": [],
            "enterprise_permissions": []
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserCompanyAdminPermission.objects.filter(user=self.test_user, company=self.company1).exists())
        self.assertFalse(UserGroupAdminPermission.objects.filter(user=self.test_user).exists())
        self.assertFalse(UserEnterpriseDataPermission.objects.filter(user=self.test_user).exists())

    def test_configure_as_group_admin(self):
        payload = {
            "user_id": self.test_user.id,
            "is_company_admin": False,
            "company_id": None,
            "group_admin_for": [self.group1_1.id],
            "enterprise_permissions": []
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(UserCompanyAdminPermission.objects.filter(user=self.test_user).exists())
        self.assertTrue(UserGroupAdminPermission.objects.filter(user=self.test_user, group=self.group1_1).exists())
        self.assertFalse(UserEnterpriseDataPermission.objects.filter(user=self.test_user).exists())

    def test_configure_enterprise_permissions(self):
        payload = {
            "user_id": self.test_user.id,
            "is_company_admin": False,
            "company_id": None,
            "group_admin_for": [],
            "enterprise_permissions": [{
                "enterprise_id": self.enterprise1_1_1.id,
                "permission_codes": ["biz_data_cfg", "fin_data_cfg"]
            }]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(UserCompanyAdminPermission.objects.filter(user=self.test_user).exists())
        self.assertFalse(UserGroupAdminPermission.objects.filter(user=self.test_user).exists())
        uedp = UserEnterpriseDataPermission.objects.get(user=self.test_user, enterprise=self.enterprise1_1_1)
        self.assertEqual(uedp.data_permissions.count(), 2)
        self.assertTrue(uedp.data_permissions.filter(code="biz_data_cfg").exists())
        self.assertTrue(uedp.data_permissions.filter(code="fin_data_cfg").exists())

    def test_configure_company_admin_clears_others(self):
        # First, set some group/enterprise perms
        UserGroupAdminPermission.objects.create(user=self.test_user, group=self.group1_1)
        uedp_initial = UserEnterpriseDataPermission.objects.create(user=self.test_user, enterprise=self.enterprise1_1_1)
        uedp_initial.data_permissions.add(self.dp_biz)

        # Now, configure as company admin
        payload = {
            "user_id": self.test_user.id,
            "is_company_admin": True,
            "company_id": self.company1.id,
        } # Minimal payload, defaults for others
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserCompanyAdminPermission.objects.filter(user=self.test_user, company=self.company1).exists())
        self.assertFalse(UserGroupAdminPermission.objects.filter(user=self.test_user).exists(), "Group admin perm should be cleared")
        self.assertFalse(UserEnterpriseDataPermission.objects.filter(user=self.test_user).exists(), "Enterprise perm should be cleared")

    def test_configure_validation_company_admin_needs_company_id(self):
        payload = {
            "user_id": self.test_user.id,
            "is_company_admin": True,
            # "company_id": self.company1.id, # Missing company_id
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company_id", response.data)

    def test_configure_validation_company_admin_exclusive(self):
        payload = {
            "user_id": self.test_user.id,
            "is_company_admin": True,
            "company_id": self.company1.id,
            "group_admin_for": [self.group1_1.id], # Should not be present if company admin
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Default DRF validation errors are often under "non_field_errors" or a specific field.
        # If raised as `serializers.ValidationError("message")` directly in `validate`, it's often `non_field_errors`.
        self.assertTrue("If user is a Company Admin" in str(response.data.get('non_field_errors', '')) or \
                        "If user is a Company Admin" in str(response.data.get('detail', '')))


    def test_configure_validation_enterprise_perm_under_group_admin(self):
        payload = {
            "user_id": self.test_user.id,
            "is_company_admin": False,
            "group_admin_for": [self.group1_1.id], # Admin for group1_1
            "enterprise_permissions": [{ # Specific perm for enterprise under group1_1
                "enterprise_id": self.enterprise1_1_1.id, # This enterprise is in group1_1
                "permission_codes": ["biz_data_cfg"]
            }]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        expected_error_msg = f"Cannot set specific permissions for enterprise {self.enterprise1_1_1.id}"
        self.assertTrue(expected_error_msg in str(response.data.get('non_field_errors', '')) or \
                        expected_error_msg in str(response.data.get('detail', '')))


    def test_get_user_data_permission_config(self):
        # Configure user as group admin for group1_1 and specific perm for an enterprise in another group
        company2 = Company.objects.create(name="Config Company 2")
        group2_1 = PermissionGroup.objects.create(name="Config Group 2.1", company=company2)
        enterprise2_1_1 = Enterprise.objects.create(name="Config Ent 2.1.1", group=group2_1)

        UserGroupAdminPermission.objects.create(user=self.test_user, group=self.group1_1)
        uedp = UserEnterpriseDataPermission.objects.create(user=self.test_user, enterprise=enterprise2_1_1)
        uedp.data_permissions.add(self.dp_biz)

        url_get = f"{self.url}?user_id={self.test_user.id}"
        response = self.client.get(url_get)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['user_id'], self.test_user.id)
        self.assertFalse(data['is_company_admin'])
        self.assertIsNone(data['company_id'])
        self.assertEqual(len(data['group_admin_for']), 1)
        self.assertIn(self.group1_1.id, data['group_admin_for'])

        self.assertEqual(len(data['enterprise_permissions']), 1)
        ep_data = data['enterprise_permissions'][0]
        self.assertEqual(ep_data['enterprise_id'], enterprise2_1_1.id)
        self.assertIn(self.dp_biz.code, ep_data['permission_codes'])
