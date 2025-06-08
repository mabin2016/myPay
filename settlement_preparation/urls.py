from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AlipayISVInitiateAuthView,
    AlipayISVAuthCallbackView,
    MerchantOnboardingViewSet,
    UserVerificationView
)

router = DefaultRouter()
router.register(r'merchant-onboarding', MerchantOnboardingViewSet, basename='merchant-onboarding')

urlpatterns = [
    path('alipay/isv-initiate-auth/', AlipayISVInitiateAuthView.as_view(), name='alipay-isv-initiate-auth'),
    path('alipay/isv-auth-callback/', AlipayISVAuthCallbackView.as_view(), name='alipay-isv-auth-callback'),
    path('user-verification/', UserVerificationView.as_view(), name='user-verification'),
    path('', include(router.urls)), # For ViewSet actions like 'start_onboarding'
]

# URLs generated:
# /api/v1/preparation/alipay/isv-initiate-auth/
# /api/v1/preparation/alipay/isv-auth-callback/
# /api/v1/preparation/user-verification/
# /api/v1/preparation/merchant-onboarding/start/
# /api/v1/preparation/merchant-onboarding/{merchant_pk}/configure-subject/
# /api/v1/preparation/merchant-onboarding/{merchant_pk}/submit-approval/
