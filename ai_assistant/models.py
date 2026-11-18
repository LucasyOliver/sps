from django.core.exceptions import ValidationError
from django.db import models
from accounts.models import UserRoleChoices
from base.models import TenantScopedModel


class MessageSenderChoices(models.TextChoices):
    USER = 'user', 'Usuário'
    ASSISTANT = 'assistant', 'Assistente IA'


ALLOWED_ASSISTANT_ROLES = (
    UserRoleChoices.GESTOR,
    UserRoleChoices.RECEPCIONISTA,
)


class AssistantChatSession(TenantScopedModel):
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='assistant_sessions',
        verbose_name='Usuário autenticado',
    )
    title = models.CharField(
        'Título da sessão',
        max_length=160,
        default='Consulta Gerencial',
    )
    llm_model_snapshot = models.CharField(
        'Modelo LLM configurado',
        max_length=120,
        default='a_definir',
    )
    is_active = models.BooleanField('Ativa', default=True)

    class Meta:
        verbose_name = 'Sessão do assistente de IA'
        verbose_name_plural = 'Sessões do assistente de IA'
        ordering = ['-updated_at', '-id']

    def __str__(self):
        return f'Sessão #{self.pk} — {self.user.full_name} ({self.salon.trade_name})'

    def clean(self):
        super().clean()
        errors = {}
        if self.salon_id and self.user_id:
            if self.user.salon_id != self.salon_id:
                errors['user'] = 'O usuário da sessão pertence a outro salão.'
            if self.user.role not in ALLOWED_ASSISTANT_ROLES:
                errors['user'] = (
                    'Apenas Gestor e Recepcionista possuem acesso ao Assistente Gerencial de IA.'
                )
        if errors:
            raise ValidationError(errors)


class AssistantChatMessage(TenantScopedModel):
    session = models.ForeignKey(
        AssistantChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Sessão de chat',
    )
    sender_role = models.CharField(
        'Origem da mensagem',
        max_length=15,
        choices=MessageSenderChoices.choices,
    )
    content = models.TextField('Conteúdo')
    invoked_tools = models.JSONField(
        'Tools acionadas na resposta',
        default=list,
        blank=True,
    )

    class Meta:
        verbose_name = 'Mensagem do assistente de IA'
        verbose_name_plural = 'Mensagens do assistente de IA'
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'[{self.get_sender_role_display()}] Sessão #{self.session_id}: {self.content[:50]}'

    def clean(self):
        super().clean()
        if (
            self.salon_id
            and self.session_id
            and self.session.salon_id != self.salon_id
        ):
            raise ValidationError(
                {'session': 'A sessão informada pertence a outro salão.'}
            )
