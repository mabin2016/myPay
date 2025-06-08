from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RiskControlConfigViewSet,
    WhitelistConfigViewSet,
    IpConfigViewSet
)

router = DefaultRouter()
router.register(r'risk-controls', RiskControlConfigViewSet, basename='riskcontrolconfig')
router.register(r'whitelists', WhitelistConfigViewSet, basename='whitelistconfig')
router.register(r'ip-configs', IpConfigViewSet, basename='ipconfig')

urlpatterns = [
    path('', include(router.urls)),
]

# Example URLs generated:
# /api/v1/configurations/risk-controls/
# /api/v1/configurations/whitelists/
# /api/v1/configurations/ip-configs/
