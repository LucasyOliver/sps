from django.urls import path
from reports.views import (
    CashClosingReportPdfView,
    CommissionReportPdfView,
    InventoryReportPdfView,
    ManagerialDashboardView,
)

app_name = 'reports'

urlpatterns = [
    path('', ManagerialDashboardView.as_view(), name='dashboard'),
    path('pdf/comissoes/', CommissionReportPdfView.as_view(), name='pdf_commissions'),
    path(
        'pdf/caixa/<int:session_pk>/',
        CashClosingReportPdfView.as_view(),
        name='pdf_cash_closing',
    ),
    path('pdf/estoque/', InventoryReportPdfView.as_view(), name='pdf_inventory'),
]
