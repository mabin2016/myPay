from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PaymentChannelViewSet,
    ArrivalChannelViewSet,
    PaymentSubjectViewSet,
    OrderRuleViewSet
)

router = DefaultRouter()
router.register(r'channels', PaymentChannelViewSet, basename='paymentchannel')
router.register(r'arrival-channels', ArrivalChannelViewSet, basename='arrivalchannel')
router.register(r'subjects', PaymentSubjectViewSet, basename='paymentsubject')
router.register(r'order-rules', OrderRuleViewSet, basename='orderrule')

urlpatterns = [
    path('', include(router.urls)),
]

# Example URLs generated:
# /api/v1/payment-channels/channels/
# /api/v1/payment-channels/channels/{id}/
# /api/v1/payment-channels/arrival-channels/
# /api/v1/payment-channels/subjects/
# /api/v1/payment-channels/order-rules/
