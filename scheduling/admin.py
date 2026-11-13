from django.contrib import admin
from scheduling.models import (
    Appointment,
    AppointmentItem,
    ProfessionalSchedule,
    ScheduleBlock,
)


class AppointmentItemInline(admin.TabularInline):
    model = AppointmentItem
    extra = 0


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'client',
        'professional',
        'salon',
        'start_at',
        'end_at',
        'total_duration_minutes',
        'total_estimated_amount',
        'status',
    )
    list_filter = ('salon', 'status', 'professional')
    search_fields = ('client__full_name', 'professional__full_name', 'salon__trade_name')
    inlines = [AppointmentItemInline]


@admin.register(ProfessionalSchedule)
class ProfessionalScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'professional',
        'salon',
        'weekday',
        'is_working',
        'start_time',
        'end_time',
    )
    list_filter = ('salon', 'weekday', 'is_working')


@admin.register(ScheduleBlock)
class ScheduleBlockAdmin(admin.ModelAdmin):
    list_display = (
        'professional',
        'salon',
        'block_type',
        'start_at',
        'end_at',
        'reason',
    )
    list_filter = ('salon', 'block_type')
