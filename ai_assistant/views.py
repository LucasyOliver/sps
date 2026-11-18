from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView
from base.mixins import RecepcaoOrGestorMixin
from ai_assistant.forms import AssistantPromptForm
from ai_assistant.models import AssistantChatSession
from ai_assistant.services import AssistantChatService, LLMFactory


class AssistantChatView(RecepcaoOrGestorMixin, FormView):
    """
    Interface de chat do Assistente Gerencial Interno (S09-T04, RF-012).
    Restrita a Gestor e Recepcionista (Profissional recebe 403 Forbidden).
    """

    form_class = AssistantPromptForm
    template_name = 'ai_assistant/chat.html'

    def _get_session(self) -> AssistantChatSession:
        raw_session_id = self.request.GET.get('session', '').strip()
        session_id = int(raw_session_id) if raw_session_id.isdigit() else None
        return AssistantChatService.get_or_create_active_session(
            salon=self.request.salon,
            user=self.request.user,
            session_id=session_id,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self._get_session()
        context['chat_session'] = session
        context['chat_messages'] = session.messages.all()
        context['user_sessions'] = AssistantChatSession.objects.for_salon(
            self.request.salon
        ).filter(user=self.request.user, is_active=True)[:10]
        context['configured_llm_model'] = LLMFactory.get_configured_model_name()
        return context

    def form_valid(self, form):
        session = self._get_session()
        try:
            AssistantChatService.send_user_message(
                salon=self.request.salon,
                user=self.request.user,
                session=session,
                prompt=form.cleaned_data['prompt'],
            )
        except ValidationError as exc:
            for msg in exc.messages:
                messages.error(self.request, msg)
            return self.form_invalid(form)

        return redirect(f'{reverse("ai_assistant:chat")}?session={session.pk}')
