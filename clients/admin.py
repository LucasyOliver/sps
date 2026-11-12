from django.contrib import admin
from clients.models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'phone',
        'email',
        'cpf_cnpj',
        'salon',
        'is_active',
        'created_at',
    )
    list_filter = ('salon', 'is_active', 'address_state')
    search_fields = ('full_name', 'phone', 'email', 'cpf_cnpj', 'salon__trade_name')
