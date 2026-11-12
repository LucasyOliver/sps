from django.contrib import admin
from salons.models import Salon


@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    list_display = (
        'trade_name',
        'slug',
        'cnpj',
        'tax_regime',
        'is_partner_salon_regime',
        'cancellation_min_hours',
        'is_active',
        'created_at',
    )
    list_filter = ('is_active', 'tax_regime', 'is_partner_salon_regime')
    search_fields = ('trade_name', 'name', 'slug', 'cnpj', 'email')
    prepopulated_fields = {'slug': ('trade_name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (
            'Identificação e Operação',
            {
                'fields': (
                    'trade_name',
                    'name',
                    'slug',
                    'phone',
                    'email',
                    'timezone',
                    'cancellation_min_hours',
                    'is_active',
                )
            },
        ),
        (
            'Preparação Fiscal (NFS-e / NFC-e)',
            {
                'fields': (
                    'cnpj',
                    'municipal_registration',
                    'state_registration',
                    'tax_regime',
                    'is_partner_salon_regime',
                    'ibge_city_code',
                )
            },
        ),
        (
            'Endereço do Estabelecimento',
            {
                'fields': (
                    'address_street',
                    'address_number',
                    'address_complement',
                    'address_neighborhood',
                    'address_city',
                    'address_state',
                    'address_zip_code',
                )
            },
        ),
        (
            'Auditoria',
            {'fields': ('created_at', 'updated_at')},
        ),
    )
