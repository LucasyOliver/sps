from django.contrib import admin
from inventory.models import Product, StockMovement


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'salon',
        'sku',
        'usage_type',
        'sale_price',
        'current_stock',
        'min_stock_alert',
        'ncm_code',
        'is_active',
    )
    list_filter = ('salon', 'usage_type', 'is_active')
    search_fields = ('name', 'sku', 'ncm_code', 'salon__trade_name')
    readonly_fields = ('current_stock',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'product',
        'salon',
        'movement_type',
        'quantity_delta',
        'balance_after',
        'order',
        'actor',
    )
    list_filter = ('salon', 'movement_type')
    search_fields = ('product__name', 'reason', 'salon__trade_name')

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
