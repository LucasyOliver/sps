from django.urls import path
from inventory.views import (
    ProductCreateView,
    ProductListView,
    ProductUpdateView,
    StockMovementCreateView,
    StockMovementListView,
)

app_name = 'inventory'

urlpatterns = [
    path('produtos/', ProductListView.as_view(), name='product_list'),
    path('produtos/novo/', ProductCreateView.as_view(), name='product_create'),
    path('produtos/<int:pk>/editar/', ProductUpdateView.as_view(), name='product_edit'),
    path('movimentacoes/', StockMovementListView.as_view(), name='movement_list'),
    path('movimentacoes/nova/', StockMovementCreateView.as_view(), name='movement_create'),
]
