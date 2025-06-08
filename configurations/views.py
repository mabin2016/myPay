from rest_framework import viewsets, status
from django.http import Http404
from core.permissions import IsAdminUserOrReadOnly # Ensure this permission is appropriate
from core.responses import api_success_response, api_error_response, api_not_found_response

from .models import RiskControlConfig, WhitelistConfig, IpConfig
from .serializers import (
    RiskControlConfigSerializer,
    WhitelistConfigSerializer,
    IpConfigSerializer
)

class RiskControlConfigViewSet(viewsets.ModelViewSet):
    queryset = RiskControlConfig.objects.all().order_by('-created_at')
    serializer_class = RiskControlConfigSerializer
    permission_classes = [IsAdminUserOrReadOnly]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return api_success_response(
                data=paginated_response.data,
                message="Risk control configurations listed.",
                count=paginated_response.data.get('count'),
                next=paginated_response.data.get('next'),
                previous=paginated_response.data.get('previous')
            )
        serializer = self.get_serializer(queryset, many=True)
        return api_success_response(data=serializer.data, message="Risk control configurations listed.")

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Risk control configuration not found.")
        serializer = self.get_serializer(instance)
        return api_success_response(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return api_success_response(data=serializer.data, message="Risk control configuration created.", status_code=status.HTTP_201_CREATED)
        return api_error_response(message="Creation failed.", errors=serializer.errors)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Risk control configuration not found.")
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        if serializer.is_valid():
            self.perform_update(serializer)
            return api_success_response(data=serializer.data, message="Risk control configuration updated.")
        return api_error_response(message="Update failed.", errors=serializer.errors)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return api_not_found_response(message="Risk control configuration not found.")
        self.perform_destroy(instance)
        return api_success_response(message="Risk control configuration deleted.", status_code=status.HTTP_200_OK)


class WhitelistConfigViewSet(viewsets.ModelViewSet):
    queryset = WhitelistConfig.objects.all().order_by('-created_at')
    serializer_class = WhitelistConfigSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    # TODO: Implement custom response handlers similar to RiskControlConfigViewSet for consistency if not done by a base class or mixin.


class IpConfigViewSet(viewsets.ModelViewSet):
    queryset = IpConfig.objects.all().order_by('-created_at')
    serializer_class = IpConfigSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    # TODO: Implement custom response handlers similar to RiskControlConfigViewSet for consistency.
