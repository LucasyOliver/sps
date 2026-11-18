from django.contrib import admin
from fiscal.models import FiscalDocumentRecord


@admin.register(FiscalDocumentRecord)
class FiscalDocumentRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'salon',
        'order',
        'document_scope',
        'status',
        'external_provider_name',
        'created_at',
    )
    list_filter = ('salon', 'document_scope', 'status')
    search_fields = ('order__id', 'salon__trade_name', 'access_key', 'fiscal_number')
    readonly_fields = (
        'issuer_snapshot',
        'customer_snapshot',
        'services_fiscal_payload',
        'products_fiscal_payload',
        'attempt_logs',
        'created_at',
        'updated_at',
    )
