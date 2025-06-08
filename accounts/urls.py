from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AccountViewSet,
    WithdrawalViewSet,
    TransactionLedgerViewSet,
    RechargeInvoiceViewSet,
    ElectronicReceiptViewSet
)

router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='account') # ReadOnly, with custom 'record-deposit' action
router.register(r'withdrawals', WithdrawalViewSet, basename='withdrawal') # Create, List, Retrieve
router.register(r'ledgers', TransactionLedgerViewSet, basename='transactionledger') # ReadOnly
router.register(r'recharge-invoices', RechargeInvoiceViewSet, basename='rechargeinvoice') # Create, List, Retrieve
router.register(r'electronic-receipts', ElectronicReceiptViewSet, basename='electronicreceipt') # ReadOnly

urlpatterns = [
    path('', include(router.urls)),
]

# Example URLs:
# /api/v1/accounts/accounts/
# /api/v1/accounts/accounts/{id}/
# /api/v1/accounts/accounts/{id}/record-deposit/
# /api/v1/accounts/withdrawals/
# /api/v1/accounts/withdrawals/{id}/
# /api/v1/accounts/ledgers/
# /api/v1/accounts/recharge-invoices/
# /api/v1/accounts/electronic-receipts/
