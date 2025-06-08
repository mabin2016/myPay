from rest_framework import viewsets, status, serializers # Added serializers for ValidationError
from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsAdminUserOrReadOnly # General admin permission
from core.responses import api_success_response, api_error_response, api_not_found_response

from .models import PaymentChannel, ArrivalChannel, PaymentSubject, OrderRule
from .serializers import (
    PaymentChannelSerializer,
    ArrivalChannelSerializer,
    PaymentSubjectSerializer,
    OrderRuleSerializer
)

class PaymentChannelViewSet(viewsets.ModelViewSet):
    queryset = PaymentChannel.objects.all().order_by('-created_at')
    serializer_class = PaymentChannelSerializer
    permission_classes = [IsAdminUserOrReadOnly]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return api_success_response(
                data=paginated_response.data,
                message="Payment channels listed.",
                count=paginated_response.data.get('count'),
                next=paginated_response.data.get('next'),
                previous=paginated_response.data.get('previous')
            )
        serializer = self.get_serializer(queryset, many=True)
        return api_success_response(data=serializer.data, message="Payment channels listed.")

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Payment channel not found.")
        serializer = self.get_serializer(instance)
        return api_success_response(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return api_success_response(data=serializer.data, message="Payment channel created.", status_code=status.HTTP_201_CREATED)
        return api_error_response(message="Creation failed.", errors=serializer.errors)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Payment channel not found.")
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        if serializer.is_valid():
            self.perform_update(serializer)
            return api_success_response(data=serializer.data, message="Payment channel updated.")
        return api_error_response(message="Update failed.", errors=serializer.errors)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Payment channel not found.")
        self.perform_destroy(instance)
        return api_success_response(message="Payment channel deleted.", status_code=status.HTTP_200_OK)


class ArrivalChannelViewSet(viewsets.ModelViewSet):
    queryset = ArrivalChannel.objects.select_related('payment_channel').order_by('-created_at')
    serializer_class = ArrivalChannelSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    # TODO: Implement custom response handlers like in PaymentChannelViewSet for consistency.


class PaymentSubjectViewSet(viewsets.ModelViewSet):
    queryset = PaymentSubject.objects.select_related('signing_company', 'payment_channel').order_by('-created_at')
    serializer_class = PaymentSubjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated: # Should be caught by IsAuthenticated permission
            return PaymentSubject.objects.none()
        if user.is_staff or user.is_superuser: # Platform admin can see all
            return super().get_queryset()

        if hasattr(user, 'signing_company') and user.signing_company is not None:
            return super().get_queryset().filter(signing_company=user.signing_company)

        return PaymentSubject.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return api_success_response(
                data=paginated_response.data,
                message="Payment subjects listed.",
                count=paginated_response.data.get('count'),
                next=paginated_response.data.get('next'),
                previous=paginated_response.data.get('previous')
                )
        serializer = self.get_serializer(queryset, many=True)
        return api_success_response(data=serializer.data, message="Payment subjects listed.")

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object() # Relies on get_queryset filtering for non-admins
        except Http404:
            return api_not_found_response(message="Payment subject not found or access denied.")

        # For non-staff/superusers, get_queryset already filters by signing_company.
        # If an object is returned, it means the user has permission.
        serializer = self.get_serializer(instance)
        return api_success_response(data=serializer.data)

    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_staff or user.is_superuser):
            if not hasattr(user, 'signing_company') or user.signing_company is None:
                # This should ideally be caught by serializer validation or permission check earlier
                raise serializers.ValidationError("You are not associated with a signing company and cannot create payment subjects.")
            # For non-admin, force the signing_company to be their own.
            serializer.save(signing_company=user.signing_company)
        else:
            # Admin can specify signing_company from request data (validated by serializer)
            serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                self.perform_create(serializer)
            except serializers.ValidationError as e: # Catch validation errors from perform_create
                 return api_error_response(message="Creation failed due to validation error.", errors=e.detail, status_code=status.HTTP_400_BAD_REQUEST)
            return api_success_response(data=serializer.data, message="Payment subject created.", status_code=status.HTTP_201_CREATED)
        return api_error_response(message="Creation failed due to invalid input.", errors=serializer.errors)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object() # get_queryset handles basic access for non-admins
        except Http404:
            return api_not_found_response(message="Payment subject not found or access denied.")

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            # Prevent non-admins from changing the signing_company
            if not (request.user.is_staff or request.user.is_superuser):
                if 'signing_company' in request.data and instance.signing_company.pk != request.data.get('signing_company'):
                    return api_error_response(message="Cannot change the signing company.", status_code=status.HTTP_403_FORBIDDEN)

            self.perform_update(serializer)
            return api_success_response(data=serializer.data, message="Payment subject updated.")
        return api_error_response(message="Update failed.", errors=serializer.errors)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Payment subject not found or access denied.")
        self.perform_destroy(instance)
        return api_success_response(message="Payment subject deleted.", status_code=status.HTTP_200_OK)


class OrderRuleViewSet(viewsets.ModelViewSet):
    queryset = OrderRule.objects.all().order_by('-created_at')
    serializer_class = OrderRuleSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    # TODO: Implement custom response handlers like in PaymentChannelViewSet for consistency.
