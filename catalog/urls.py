from django.urls import path
from catalog.views import (
    CommissionRuleCreateView,
    CommissionRuleDeleteView,
    CommissionRuleListView,
    CommissionRuleUpdateView,
    ServiceCategoryCreateView,
    ServiceCategoryListView,
    ServiceCategoryUpdateView,
    ServiceCreateView,
    ServiceListView,
    ServiceUpdateView,
)

app_name = 'catalog'

urlpatterns = [
    path('servicos/', ServiceListView.as_view(), name='service_list'),
    path('servicos/novo/', ServiceCreateView.as_view(), name='service_create'),
    path('servicos/<int:pk>/editar/', ServiceUpdateView.as_view(), name='service_edit'),
    path('categorias/', ServiceCategoryListView.as_view(), name='category_list'),
    path('categorias/nova/', ServiceCategoryCreateView.as_view(), name='category_create'),
    path('categorias/<int:pk>/editar/', ServiceCategoryUpdateView.as_view(), name='category_edit'),
    path('comissoes/', CommissionRuleListView.as_view(), name='commission_rule_list'),
    path('comissoes/nova/', CommissionRuleCreateView.as_view(), name='commission_rule_create'),
    path('comissoes/<int:pk>/editar/', CommissionRuleUpdateView.as_view(), name='commission_rule_edit'),
    path('comissoes/<int:pk>/excluir/', CommissionRuleDeleteView.as_view(), name='commission_rule_delete'),
]
