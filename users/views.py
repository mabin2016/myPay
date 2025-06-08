from django.contrib.auth import get_user_model
from rest_framework import viewsets, mixins, status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework.decorators import action
from rest_framework.response import Response as DRFResponse # Alias to avoid conflict with core.responses

from core.permissions import IsSuperUserOrReadOnly, IsObjectOwnerOrReadOnly, IsAdminUserOrReadOnly
from core.responses import api_success_response, api_error_response, api_not_found_response # Using custom responses

from .models import Role, Permission, Menu, UserRoleMap, RolePermissionMap, RoleMenuMap
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    CustomTokenObtainPairSerializer,
    RoleSerializer,
    PermissionSerializer,
    MenuSerializer,
    UserRoleMapSerializer,
    RolePermissionMapSerializer,
    RoleMenuMapSerializer
)
# Import UserSigningContractSerializer from organizations.serializers
from organizations.serializers import UserSigningContractSerializer
from organizations.models import SigningCompany

User = get_user_model()

class UserRegistrationViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.none() # No listing needed for registration
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny] # Anyone can register

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_data = UserSerializer(user, context=self.get_serializer_context()).data # Use UserSerializer for response
            return api_success_response(data=user_data, message="User registered successfully.", status_code=status.HTTP_201_CREATED)
        return api_error_response(message="Registration failed.", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAdminUser]
        elif self.action == 'list':
            permission_classes = [IsAdminUser]
        elif self.action in ['retrieve', 'update', 'partial_update']:
            permission_classes = [IsAuthenticated, IsObjectOwnerOrReadOnly | IsAdminUser]
        elif self.action == 'destroy':
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='me', url_name='me')
    def get_current_user(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        return api_success_response(data=serializer.data, message="Current user data retrieved.")

    def create(self, request, *args, **kwargs):
        # This endpoint is typically for admins to create users. Registration is separate.
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return api_success_response(data=serializer.data, message="User created by admin.", status_code=status.HTTP_201_CREATED) #, headers=headers)
        return api_error_response(message="Admin user creation failed.", errors=serializer.errors)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return api_success_response(data=serializer.data, message="User updated successfully.")
        return api_error_response(message="Update failed.", errors=serializer.errors)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        # Standard HTTP 204 No Content response should not have a body.
        # For consistency with our JSON responses, we can send a 200 OK with a message.
        return api_success_response(message="User deleted successfully.", status_code=status.HTTP_200_OK) # Or status.HTTP_204_NO_CONTENT without data

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
             return api_not_found_response(message="User not found.")
        serializer = self.get_serializer(instance)
        return api_success_response(data=serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            # Wrap paginated_response.data in our custom format
            return api_success_response(
                data=paginated_response.data,
                message="Users listed successfully.",
                # Pass count, next, previous if available in paginated_response.data
                # count=paginated_response.data.get('count'),
                # next_page=paginated_response.data.get('next'), # Renamed to avoid clash with DRF Response.next
                # previous_page=paginated_response.data.get('previous')
            )

        serializer = self.get_serializer(queryset, many=True)
        return api_success_response(data=serializer.data, message="Users listed successfully.")

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], # Or IsAdminUser if only admins can do this for others
            url_path='sign-contract', url_name='sign_contract',
            serializer_class=UserSigningContractSerializer) # Specify serializer for schema generation
    def sign_contract(self, request, pk=None):
        """
        Associates a user with a signing company and records contract details.
        Expects 'signing_company_id' and optional 'contract_details' in request data.
        The 'user_id' in UserSigningContractSerializer is validated against the user from the URL (pk).
        """
        try:
            user = self.get_object() # Gets user instance based on pk from URL
        except Http404:
            return api_not_found_response(message="User not found.")

        serializer = UserSigningContractSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error_response(message="Validation failed.", errors=serializer.errors)

        data = serializer.validated_data

        # Ensure the user_id from serializer matches the user from URL if both are present
        # Or, if user_id is not part of URL (e.g. action on /users/me/sign-contract), then use request.user
        # Here, pk is user_id from URL. If serializer also has user_id, ensure they match.
        if data.get('user_id') and data.get('user_id') != user.id:
             return api_error_response(message="User ID in request body does not match user ID in URL.", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            signing_company = SigningCompany.objects.get(pk=data['signing_company_id'])
        except SigningCompany.DoesNotExist:
            return api_not_found_response(message="Signing company not found.")

        # Update user record
        user.signing_company = signing_company
        user.contract_details = data.get('contract_details', user.contract_details) # Keep old if not provided
        user.save()

        # Return updated user data
        user_serializer = UserSerializer(user, context={'request': request})
        return api_success_response(data=user_serializer.data, message="User successfully signed contract with company.")


class CustomTokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        # Use DRF's Response for the initial processing by SimpleJWT
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # If token generation is successful, wrap it in our custom success response
            return api_success_response(data=response.data, message="Login successful.")
        else:
            # If SimpleJWT returns an error (e.g., invalid credentials),
            # wrap its error response in our custom error response format.
            error_detail = response.data.get("detail", "Authentication failed.")
            error_code = response.data.get("code", None)
            errors = {"non_field_errors": [error_detail]}
            if error_code:
                errors["code"] = error_code
            return api_error_response(message=str(error_detail), errors=errors, status_code=response.status_code)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUserOrReadOnly]

class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAdminUserOrReadOnly]

class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.all().order_by('order', 'name')
    serializer_class = MenuSerializer
    permission_classes = [IsAdminUserOrReadOnly]

class UserRoleMapViewSet(viewsets.ModelViewSet):
    queryset = UserRoleMap.objects.all()
    serializer_class = UserRoleMapSerializer
    permission_classes = [IsAdminUser]

class RolePermissionMapViewSet(viewsets.ModelViewSet):
    queryset = RolePermissionMap.objects.all()
    serializer_class = RolePermissionMapSerializer
    permission_classes = [IsAdminUser]

class RoleMenuMapViewSet(viewsets.ModelViewSet):
    queryset = RoleMenuMap.objects.all()
    serializer_class = RoleMenuMapSerializer
    permission_classes = [IsAdminUser]
