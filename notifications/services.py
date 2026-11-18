from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from notifications.models import (
    NotificationLog,
    NotificationStatusChoices,
    NotificationTypeChoices,
)
from scheduling.models import (
    ACTIVE_APPOINTMENT_STATUSES,
    Appointment,
    AppointmentStatusChoices,
)


class NotificationService:
    """
    Serviço idempotente de notificações e lembretes por e-mail (S08-T02, RF-010, SEC-F).
    Garante que cada combinação (appointment, notification_type, reference_window) dispare
    no máximo 1 e-mail e revalida no banco que o salão e o agendamento continuam elegíveis.
    """

    @staticmethod
    def _build_subject_and_body(appointment: Appointment, notification_type: str) -> tuple[str, str]:
        local_start = timezone.localtime(appointment.start_at)
        salon_name = appointment.salon.trade_name
        prof_name = appointment.professional.full_name
        client_name = appointment.client.full_name
        formatted_dt = local_start.strftime('%d/%m/%Y às %H:%M')

        if notification_type == NotificationTypeChoices.CONFIRMATION:
            subject = f'[{salon_name}] Confirmação de Agendamento — {formatted_dt}'
            body = (
                f'Olá, {client_name}!\n\n'
                f'Seu agendamento em {salon_name} com {prof_name} foi registrado para {formatted_dt}.\n'
                f'Valor total estimado: R$ {appointment.total_estimated_amount}\n'
                f'Código público de consulta/cancelamento: {appointment.public_token}\n'
            )
        elif notification_type == NotificationTypeChoices.CANCELLATION:
            subject = f'[{salon_name}] Aviso de Cancelamento — {formatted_dt}'
            body = (
                f'Olá, {client_name}.\n\n'
                f'Seu agendamento em {salon_name} previsto para {formatted_dt} foi cancelado.\n'
                f'Motivo: {appointment.cancellation_reason or "Não informado"}\n'
            )
        elif notification_type == NotificationTypeChoices.RESCHEDULE:
            subject = f'[{salon_name}] Aviso de Remarcação — {formatted_dt}'
            body = (
                f'Olá, {client_name}!\n\n'
                f'Seu agendamento em {salon_name} com {prof_name} foi remarcado para {formatted_dt}.\n'
            )
        else:
            subject = f'[{salon_name}] Lembrete de Atendimento — {formatted_dt}'
            body = (
                f'Olá, {client_name}!\n\n'
                f'Lembramos do seu atendimento agendado em {salon_name} com {prof_name} '
                f'em {formatted_dt}.\n'
            )
        return subject, body

    @classmethod
    def dispatch_appointment_notification(
        cls,
        *,
        salon_id: int,
        appointment_id: int,
        notification_type: str,
        reference_window: str = '',
    ) -> tuple[NotificationLog | None, bool]:
        """
        Retorna (log, created_and_sent).
        Se já existir NotificationLog para a mesma janela, retorna (existing_log, False)
        sem reenviar o e-mail.
        """
        appointment = (
            Appointment.objects.select_related('salon', 'client', 'professional')
            .filter(pk=appointment_id, salon_id=salon_id)
            .first()
        )
        if appointment is None:
            return None, False

        local_start = timezone.localtime(appointment.start_at)
        window_key = (reference_window or '').strip() or local_start.strftime('%Y-%m-%dT%H:%M')

        existing = NotificationLog.objects.filter(
            appointment=appointment,
            notification_type=notification_type,
            reference_window=window_key,
        ).first()
        if existing is not None:
            return existing, False

        # Revalidação de estado ativo no momento da execução do worker (SEC-F)
        skip_reason = ''
        if not appointment.salon.is_active:
            skip_reason = 'Salão inativo no momento do disparo.'
        elif (
            notification_type != NotificationTypeChoices.CANCELLATION
            and appointment.status not in ACTIVE_APPOINTMENT_STATUSES
        ):
            skip_reason = (
                f'Agendamento #{appointment.pk} não está mais ativo '
                f'(status: {appointment.get_status_display()}).'
            )
        elif (
            notification_type == NotificationTypeChoices.CANCELLATION
            and appointment.status != AppointmentStatusChoices.CANCELLED
        ):
            skip_reason = 'Agendamento não consta como cancelado.'
        elif not (appointment.client.email or '').strip():
            skip_reason = 'Cliente não possui endereço de e-mail cadastrado.'

        recipient = (appointment.client.email or '').strip()
        subject, body = cls._build_subject_and_body(appointment, notification_type)

        try:
            with transaction.atomic():
                if skip_reason:
                    log = NotificationLog.objects.create(
                        salon=appointment.salon,
                        appointment=appointment,
                        notification_type=notification_type,
                        reference_window=window_key,
                        recipient_email=recipient,
                        subject=subject,
                        status=NotificationStatusChoices.SKIPPED_INACTIVE,
                        detail_message=skip_reason,
                    )
                    return log, False

                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                )
                log = NotificationLog.objects.create(
                    salon=appointment.salon,
                    appointment=appointment,
                    notification_type=notification_type,
                    reference_window=window_key,
                    recipient_email=recipient,
                    subject=subject,
                    status=NotificationStatusChoices.SENT,
                    detail_message='E-mail enviado com sucesso.',
                )
                return log, True
        except IntegrityError:
            existing = NotificationLog.objects.filter(
                appointment=appointment,
                notification_type=notification_type,
                reference_window=window_key,
            ).first()
            return existing, False

    @classmethod
    def dispatch_upcoming_reminders(cls, *, hours_ahead: int = 24, now=None) -> int:
        current_time = now or timezone.now()
        horizon = current_time + timedelta(hours=int(hours_ahead))
        upcoming = Appointment.objects.select_related('salon', 'client').filter(
            salon__is_active=True,
            status__in=ACTIVE_APPOINTMENT_STATUSES,
            start_at__gte=current_time,
            start_at__lte=horizon,
        )
        sent_count = 0
        for appt in upcoming:
            local_start = timezone.localtime(appt.start_at)
            window_key = f'reminder-{local_start:%Y-%m-%dT%H:%M}'
            _log, sent = cls.dispatch_appointment_notification(
                salon_id=appt.salon_id,
                appointment_id=appt.pk,
                notification_type=NotificationTypeChoices.REMINDER,
                reference_window=window_key,
            )
            if sent:
                sent_count += 1
        return sent_count
