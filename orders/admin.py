from django.contrib import admin
from orders.models import OrderProductItem, OrderServiceItem, ServiceOrder


class OrderServiceItemInline(admin.TabularInline):
    model = OrderServiceItem
    extra = 0
    readonly_fields = ('net_price', 'applied_commission_pct')


class OrderProductItemInline(admin.TabularInline):
    model = OrderProductItem
    extra = 0
    readonly_fields = ('total_price',)


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'salon',
        'client',
        'status',
        'subtotal_services',
        'subtotal_products',
        'discount_amount',
        'total_amount',
        'created_at',
    )
    list_filter = ('salon', 'status')
    search_fields = ('id', 'client__full_name', 'salon__trade_name')
    readonly_fields = (
        'subtotal_services',
        'subtotal_products',
        'total_amount',
        'closed_at',
        'closed_by',
        'cancelled_at',
    )
    inlines = [OrderServiceItemInline, OrderProductItemInline]
