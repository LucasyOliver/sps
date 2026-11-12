from django.contrib import admin
from catalog.models import ProfessionalServiceCommission, Service, ServiceCategory


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'salon', 'is_active', 'created_at')
    list_filter = ('salon', 'is_active')
    search_fields = ('name', 'salon__trade_name')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'salon',
        'category',
        'duration_minutes',
        'base_price',
        'default_commission_pct',
        'lc116_service_code',
        'is_active',
    )
    list_filter = ('salon', 'is_active', 'category')
    search_fields = ('name', 'lc116_service_code', 'cnae_code', 'salon__trade_name')
    filter_horizontal = ('professionals',)


@admin.register(ProfessionalServiceCommission)
class ProfessionalServiceCommissionAdmin(admin.ModelAdmin):
    list_display = (
        'professional',
        'service',
        'salon',
        'commission_pct',
        'is_active',
    )
    list_filter = ('salon', 'is_active')
    search_fields = (
        'professional__full_name',
        'service__name',
        'salon__trade_name',
    )
