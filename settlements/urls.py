from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PaymentBatchViewSet,
    PaymentOrderViewSet,
    AlipayISVCallbackView
)

router = DefaultRouter()
router.register(r'batches', PaymentBatchViewSet, basename='paymentbatch')
router.register(r'orders', PaymentOrderViewSet, basename='paymentorder')

urlpatterns = [
    path('', include(router.urls)),
    path('callbacks/alipay-isv/', AlipayISVCallbackView.as_view(), name='alipay-isv-payment-callback'), # Renamed for clarity
    path('callbacks/alipay-isv-refund/', AlipayISVRefundCallbackView.as_view(), name='alipay-isv-refund-callback'),
]

# Example URLs:
# /api/v1/settlements/batches/
# /api/v1/settlements/batches/{id}/
# /api/v1/settlements/batches/{id}/process-action/ (custom action)
# /api/v1/settlements/orders/
# /api/v1/settlements/orders/{id}/
# /api/v1/settlements/orders/{id}/initiate-refund/ (custom action)
