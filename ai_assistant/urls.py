from django.urls import path
from ai_assistant.views import AssistantChatView

app_name = 'ai_assistant'

urlpatterns = [
    path('', AssistantChatView.as_view(), name='chat'),
]
