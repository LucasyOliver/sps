from django.contrib import admin
from finance.models import (
    CashRegisterSession,
    CashTransaction,
    CommissionEntry,
    OrderPayment,
)


@admin.register(CashRegisterSession)
class CashRegisterSessionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'salon',
        'status',
        'opened_by',
        'opened_at',
        'opening_balance',
        'closing_balance_expected',
        'closing_balance_counted',
        'closed_by',
        'closed_at',
    )
    list_filter = ('salon', 'status')
    search_fields = ('id', 'salon__trade_name', 'opened_by__full_name')


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'salon',
        'cash_session',
        'transaction_type',
        'payment_method',
        'amount',
        'order',
        'created_by',
    )
    list_filter = ('salon', 'transaction_type', 'payment_method')
    search_fields = ('description', 'salon__trade_name')


@admin.register(OrderPayment)
class OrderPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'salon',
        'order',
        'cash_session',
        'payment_method',
        'amount',
        'is_reversed',
        'created_at',
    )
    list_filter = ('salon', 'payment_method', 'is_reversed')


@admin.register(CommissionEntry)
class CommissionEntryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'salon',
        'professional',
        'order',
        'base_amount',
        'commission_pct',
        'commission_amount',
        'status',
        'paid_at',
    )
    list_filter = ('salon', 'status')
    search_fields = ('professional__full_name', 'salon__trade_name')
