from django.contrib import admin
from scheduling.models import ProfessionalSchedule, ScheduleBlock


@admin.register(ProfessionalSchedule)
class ProfessionalScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'salon',
        'professional',
        'weekday',
        'is_working',
        'start_time',
        'end_time',
        'break_start_time',
        'break_end_time',
    )
    list_filter = ('salon', 'weekday', 'is_working')
    search_fields = ('professional__full_name', 'professional__email')


@admin.register(ScheduleBlock)
class ScheduleBlockAdmin(admin.ModelAdmin):
    list_display = (
        'salon',
        'professional',
        'block_type',
        'start_at',
        'end_at',
        'reason',
        'created_by',
    )
    list_filter = ('salon', 'block_type')
    search_fields = ('professional__full_name', 'reason')
