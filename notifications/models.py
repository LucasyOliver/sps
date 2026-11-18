from django.core.exceptions import ValidationError
from django.db import models
from base.models import TenantScopedModel


class NotificationTypeChoices(models.TextChoices):
    CONFIRMATION = 'confirmacao_agendamento', 'Confirmação de agendamento'
    CANCELLATION = 'cancelamento_agendamento', 'Aviso de cancelamento'
    RESCHEDULE = 'remarcacao_agendamento', 'Aviso de remarcação'
    REMINDER = 'lembrete_agendamento', 'Lembrete de agendamento próximo'


class NotificationStatusChoices(models.TextChoices):
    SENT = 'enviado', 'Enviado'
    SKIPPED_INACTIVE = 'ignorado_inativo', 'Ignorado (salão/agendamento inativo ou sem e-mail)'
    FAILED = 'falha_envio', 'Falha no envio'


class NotificationLog(TenantScopedModel):
    appointment = models.ForeignKey(
        'scheduling.Appointment',
        on_delete=models.CASCADE,
        related_name='notification_logs',
        verbose_name='Agendamento',
    )
    notification_type = models.CharField(
        'Tipo de notificação',
        max_length=30,
        choices=NotificationTypeChoices.choices,
    )
    reference_window = models.CharField(
        'Janela de referência (idempotência)',
        max_length=80,
        help_text='Chave de janela (ex.: 2026-11-18T14:00 ou window-24h) para impedir reenvio duplicado.',
    )
    recipient_email = models.EmailField('E-mail do destinatário', blank=True)
    subject = models.CharField('Assunto', max_length=200, blank=True)
    status = models.CharField(
        'Status',
        max_length=25,
        choices=NotificationStatusChoices.choices,
        default=NotificationStatusChoices.SENT,
    )
    detail_message = models.CharField('Detalhe de execução', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Log de notificação'
        verbose_name_plural = 'Logs de notificações'
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['appointment', 'notification_type', 'reference_window'],
                name='unique_appointment_notification_window',
            ),
        ]
        indexes = [
            models.Index(
                fields=['salon', 'notification_type', 'created_at'],
                name='idx_notif_salon_type_created',
            ),
        ]

    def __str__(self):
        return (
            f'Agendamento #{self.appointment_id} — '
            f'{self.get_notification_type_display()} [{self.reference_window}] ({self.get_status_display()})'
        )

    def clean(self):
        super().clean()
        if (
            self.salon_id
            and self.appointment_id
            and self.appointment.salon_id != self.salon_id
        ):
            raise ValidationError(
                {'appointment': 'O agendamento selecionado pertence a outro salão.'}
            )
