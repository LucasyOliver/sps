from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'SPS — Administração da Plataforma'
admin.site.site_title = 'SPS Admin'
admin.site.index_title = 'Gestão de Salões e Usuários'

urlpatterns = [
    path('admin/dj-celery-panel/', include('dj_celery_panel.urls')),
    path('admin/', admin.site.urls),
    path('conta/', include('accounts.urls', namespace='accounts')),
    path('salao/', include('salons.urls', namespace='salons')),
    path('agenda/', include('scheduling.urls', namespace='scheduling')),
    path('catalogo/', include('catalog.urls', namespace='catalog')),
    path('clientes/', include('clients.urls', namespace='clients')),
    path('estoque/', include('inventory.urls', namespace='inventory')),
    path('comandas/', include('orders.urls', namespace='orders')),
    path('caixa/', include('finance.urls', namespace='finance')),
    path('relatorios/', include('reports.urls', namespace='reports')),
    path('s/<slug:salon_slug>/', include('scheduling.public_urls', namespace='public_booking')),
    path('', include('base.urls', namespace='base')),
]
