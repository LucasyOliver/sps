from django.urls import path
from orders.views import (
    OrderAddProductItemView,
    OrderAddServiceItemView,
    OrderAdjustmentView,
    OrderCancelView,
    OrderRemoveProductItemView,
    OrderRemoveServiceItemView,
    ServiceOrderCreateView,
    ServiceOrderDetailView,
    ServiceOrderFromAppointmentView,
    ServiceOrderListView,
)

app_name = 'orders'

urlpatterns = [
    path('', ServiceOrderListView.as_view(), name='order_list'),
    path('nova/', ServiceOrderCreateView.as_view(), name='order_create'),
    path(
        'agendamento/<int:appointment_pk>/abrir/',
        ServiceOrderFromAppointmentView.as_view(),
        name='order_from_appointment',
    ),
    path('<int:pk>/', ServiceOrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/servicos/adicionar/', OrderAddServiceItemView.as_view(), name='order_add_service'),
    path(
        '<int:pk>/servicos/<int:item_pk>/remover/',
        OrderRemoveServiceItemView.as_view(),
        name='order_remove_service',
    ),
    path('<int:pk>/produtos/adicionar/', OrderAddProductItemView.as_view(), name='order_add_product'),
    path(
        '<int:pk>/produtos/<int:item_pk>/remover/',
        OrderRemoveProductItemView.as_view(),
        name='order_remove_product',
    ),
    path('<int:pk>/ajustes/', OrderAdjustmentView.as_view(), name='order_adjust'),
    path('<int:pk>/cancelar/', OrderCancelView.as_view(), name='order_cancel'),
]
