from django.contrib import admin
from ai_assistant.models import AssistantChatMessage, AssistantChatSession


class AssistantChatMessageInline(admin.TabularInline):
    model = AssistantChatMessage
    extra = 0
    readonly_fields = ('sender_role', 'content', 'invoked_tools', 'created_at')


@admin.register(AssistantChatSession)
class AssistantChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'salon',
        'user',
        'title',
        'llm_model_snapshot',
        'is_active',
        'updated_at',
    )
    list_filter = ('salon', 'is_active', 'llm_model_snapshot')
    search_fields = ('title', 'user__full_name', 'salon__trade_name')
    inlines = [AssistantChatMessageInline]
