from django.urls import path
from finance.views import (
    CashRegisterDashboardView,
    CashSessionCloseView,
    CashSessionOpenView,
    CommissionEntryListView,
    CommissionPayoutView,
    ManualCashTransactionCreateView,
    OrderCheckoutView,
    OrderReversalView,
)

app_name = 'finance'

urlpatterns = [
    path('', CashRegisterDashboardView.as_view(), name='cash_dashboard'),
    path('abrir/', CashSessionOpenView.as_view(), name='cash_open'),
    path('fechar/', CashSessionCloseView.as_view(), name='cash_close'),
    path(
        'lancamento/',
        ManualCashTransactionCreateView.as_view(),
        name='cash_manual_tx',
    ),
    path(
        'comandas/<int:order_pk>/pagar/',
        OrderCheckoutView.as_view(),
        name='order_checkout',
    ),
    path(
        'comandas/<int:order_pk>/estornar/',
        OrderReversalView.as_view(),
        name='order_reverse',
    ),
    path('comissoes/', CommissionEntryListView.as_view(), name='commission_list'),
    path('comissoes/pagar/', CommissionPayoutView.as_view(), name='commission_payout'),
]
