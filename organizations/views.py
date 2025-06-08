from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import Http404 # Import Django's Http404
from rest_framework import viewsets, status, mixins, serializers # Added serializers to raise ValidationError
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response as DRFResponse # To distinguish from custom response

from core.permissions import IsAdminUserOrReadOnly # Using a general admin permission for now
from core.responses import api_success_response, api_error_response, api_not_found_response

from .models import SigningCompany, Group, Merchant, Platform
from .serializers import (
    SigningCompanySerializer,
    GroupSerializer,
    MerchantSerializer,
    PlatformSerializer,
    # UserSigningContractSerializer # This will be used in UserViewSet's custom action in users.views
)
# from users.models import User as CustomUserMainModel # Not needed if using get_user_model()
from users.serializers import UserSerializer # For Merchant user representation

User = get_user_model() # This is users.User due to AUTH_USER_MODEL in settings

class SigningCompanyViewSet(viewsets.ModelViewSet):
    queryset = SigningCompany.objects.all().order_by('-created_at')
    serializer_class = SigningCompanySerializer
    permission_classes = [IsAdminUserOrReadOnly]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return api_success_response(
                data=paginated_response.data,
                message="Signing companies listed.",
                count=paginated_response.data.get('count'),
                next=paginated_response.data.get('next'),
                previous=paginated_response.data.get('previous')
            )
        serializer = self.get_serializer(queryset, many=True)
        return api_success_response(data=serializer.data, message="Signing companies listed.")

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Signing company not found.")
        serializer = self.get_serializer(instance)
        return api_success_response(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return api_success_response(data=serializer.data, message="Signing company created.", status_code=status.HTTP_201_CREATED)
        return api_error_response(message="Creation failed.", errors=serializer.errors)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Signing company not found.")
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        if serializer.is_valid():
            self.perform_update(serializer)
            return api_success_response(data=serializer.data, message="Signing company updated.")
        return api_error_response(message="Update failed.", errors=serializer.errors)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Signing company not found.")
        self.perform_destroy(instance)
        return api_success_response(message="Signing company deleted.", status_code=status.HTTP_200_OK)

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by('-created_at')
    serializer_class = GroupSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    # Implement custom response handlers like in SigningCompanyViewSet for consistency if needed.

class MerchantViewSet(viewsets.ModelViewSet):
    queryset = Merchant.objects.select_related('signing_company', 'group', 'user').order_by('-created_at')
    serializer_class = MerchantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated: # Should be caught by permission_classes but good practice
            return Merchant.objects.none()
        if user.is_staff or user.is_superuser:
            return super().get_queryset()

        # Check if user is directly linked to a merchant as its admin user
        # The related name from User to Merchant (OneToOneField) is 'merchant' by default.
        if hasattr(user, 'merchant'):
            return super().get_queryset().filter(user=user)

        # If user is part of a signing company, show merchants of that company
        if hasattr(user, 'signing_company') and user.signing_company is not None:
             return super().get_queryset().filter(signing_company=user.signing_company)

        return Merchant.objects.none()

    def perform_create(self, serializer):
        # Example: If merchant_code should be auto-generated if not provided.
        # This logic is better placed in the model's save() method or serializer's create().
        # For linking user, the serializer's 'user' field (PrimaryKeyRelatedField) handles association.
        # If creating a new user during merchant creation:
        # user_data = self.request.data.get('user_details_for_new_merchant_admin')
        # if user_data:
        #     # ... create user ...
        #     # serializer.save(user=created_user, ...)
        # else:
        # serializer.save()
        serializer.save()


    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return api_success_response(
                data=paginated_response.data,
                message="Merchants listed.",
                count=paginated_response.data.get('count'),
                next=paginated_response.data.get('next'),
                previous=paginated_response.data.get('previous')
            )
        serializer = self.get_serializer(queryset, many=True)
        return api_success_response(data=serializer.data, message="Merchants listed.")

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404: # Check if this is correctly Django's Http404
            return api_not_found_response(message="Merchant not found.")
        serializer = self.get_serializer(instance)
        return api_success_response(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return api_success_response(data=serializer.data, message="Merchant created.", status_code=status.HTTP_201_CREATED)
        return api_error_response(message="Creation failed.", errors=serializer.errors)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Merchant not found.")
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        if serializer.is_valid():
            self.perform_update(serializer)
            return api_success_response(data=serializer.data, message="Merchant updated.")
        return api_error_response(message="Update failed.", errors=serializer.errors)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Merchant not found.")
        self.perform_destroy(instance)
        return api_success_response(message="Merchant deleted.", status_code=status.HTTP_200_OK)


class PlatformViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Platform.objects.all()
    serializer_class = PlatformSerializer
    permission_classes = [IsAdminUserOrReadOnly]

    def list(self, request, *args, **kwargs):
        # Platform info is usually a singleton.
        instance = self.get_queryset().first()
        if not instance:
            # Optionally, create a default platform entry if none exists and user is admin
            # if request.user.is_staff:
            #    instance = Platform.objects.create(name="Default Platform", version="1.0")
            # else:
            return api_not_found_response(message="Platform information not configured.")
        serializer = self.get_serializer(instance)
        return api_success_response(data=serializer.data, message="Platform information retrieved.")

    def retrieve(self, request, *args, **kwargs):
        # For a singleton, retrieve by known ID or just return the single instance.
        # Default retrieve by PK might not make sense if there's only one.
        return self.list(request, *args, **kwargs) # Redirect to list logic for singleton

# The "UserSigningView" (APIView) which was planned to be here,
# will be implemented as a custom action on `UserViewSet` in `users/views.py`
# as per the refinement in the task description.
# This keeps user-related actions grouped with the User resource.
