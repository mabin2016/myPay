from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SigningCompanyViewSet,
    GroupViewSet,
    MerchantViewSet,
    PlatformViewSet
)

router = DefaultRouter()
router.register(r'signing-companies', SigningCompanyViewSet, basename='signingcompany')
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'merchants', MerchantViewSet, basename='merchant')
router.register(r'platform', PlatformViewSet, basename='platform') # Typically a singleton or read-only

urlpatterns = [
    path('', include(router.urls)),
]

# URLs generated would be like:
# /api/v1/organizations/signing-companies/
# /api/v1/organizations/signing-companies/{id}/
# /api/v1/organizations/groups/
# /api/v1/organizations/merchants/
# /api/v1/organizations/platform/ (likely just list/retrieve the single platform entry)
