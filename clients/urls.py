from django.urls import path
from clients.views import (
    ClientCreateView,
    ClientDetailView,
    ClientListView,
    ClientUpdateView,
)

app_name = 'clients'

urlpatterns = [
    path('', ClientListView.as_view(), name='client_list'),
    path('novo/', ClientCreateView.as_view(), name='client_create'),
    path('<int:pk>/', ClientDetailView.as_view(), name='client_detail'),
    path('<int:pk>/editar/', ClientUpdateView.as_view(), name='client_edit'),
]
