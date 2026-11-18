from django.contrib import admin
from notifications.models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'salon',
        'appointment',
        'notification_type',
        'reference_window',
        'recipient_email',
        'status',
    )
    list_filter = ('salon', 'notification_type', 'status')
    search_fields = ('recipient_email', 'subject', 'reference_window', 'salon__trade_name')
    readonly_fields = (
        'salon',
        'appointment',
        'notification_type',
        'reference_window',
        'recipient_email',
        'subject',
        'status',
        'detail_message',
        'created_at',
        'updated_at',
    )
