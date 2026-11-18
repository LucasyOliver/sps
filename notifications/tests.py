from datetime import datetime, time, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from accounts.models import UserRoleChoices
from catalog.models import Service
from clients.models import Client
from notifications.models import (
    NotificationLog,
    NotificationStatusChoices,
    NotificationTypeChoices,
)
from notifications.services import NotificationService
from notifications.tasks import (
    dispatch_upcoming_appointment_reminders_task,
    send_appointment_notification_task,
)
from salons.models import Salon, SalonBusinessHours, WeekdayChoices
from scheduling.models import (
    Appointment,
    AppointmentStatusChoices,
    ProfessionalSchedule,
)
from scheduling.services import SchedulingService

User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class NotificationIdempotencyAndSecurityTests(TestCase):
    def setUp(self):
        self.salon = Salon.objects.create(
            name='Salão Alpha LTDA',
            trade_name='Salão Alpha',
            slug='salao-alpha',
        )
        SalonBusinessHours.objects.create(
            salon=self.salon,
            weekday=WeekdayChoices.MONDAY,
            is_open=True,
            opening_time=time(9, 0),
            closing_time=time(19, 0),
        )
        self.prof = User.objects.create_user(
            email='ana@alpha.com.br',
            password='StrongPassword123!',
            full_name='Ana Especialista',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon,
        )
        ProfessionalSchedule.objects.create(
            salon=self.salon,
            professional=self.prof,
            weekday=WeekdayChoices.MONDAY,
            is_working=True,
            start_time=time(9, 0),
            end_time=time(18, 0),
        )
        self.service = Service.objects.create(
            salon=self.salon,
            name='Corte + Finalização',
            duration_minutes=45,
            base_price=Decimal('90.00'),
        )
        self.service.professionals.add(self.prof)

        self.client_obj = Client.objects.create(
            salon=self.salon,
            full_name='Beatriz Souza',
            phone='11988887777',
            email='beatriz@cliente.com.br',
        )

    def test_reminder_task_idempotency_sends_single_email_when_executed_twice(self):
        """
        S08-T02 / S08-T05 / RF-010 Critério de aceite:
        Dado um agendamento confirmado, quando a task de lembrete rodar duas vezes para a
        mesma janela, apenas 1 e-mail de lembrete é enviado ao cliente e o histórico
        registra a execução idempotente.
        """
        now = timezone.now()
        upcoming_start = now + timedelta(hours=4)
        appt = Appointment.objects.create(
            salon=self.salon,
            client=self.client_obj,
            professional=self.prof,
            start_at=upcoming_start,
            end_at=upcoming_start + timedelta(minutes=45),
            total_duration_minutes=45,
            total_estimated_amount=Decimal('90.00'),
            status=AppointmentStatusChoices.CONFIRMED,
        )

        # 1ª execução da task periódica do Celery Beat
        res_1 = dispatch_upcoming_appointment_reminders_task.delay(hours_ahead=24).get()
        self.assertEqual(res_1['sent_count'], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Lembrete de Atendimento', mail.outbox[0].subject)

        # 2ª execução na mesma janela -> idempotente (0 novos e-mails enviados)
        res_2 = dispatch_upcoming_appointment_reminders_task.delay(hours_ahead=24).get()
        self.assertEqual(res_2['sent_count'], 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            NotificationLog.objects.filter(
                appointment=appt,
                notification_type=NotificationTypeChoices.REMINDER,
            ).count(),
            1,
        )

    def test_sec_f_task_aborts_cleanly_when_appointment_cancelled_or_salon_inactive(self):
        """
        SEC-F / RF-010: Se o agendamento for cancelado ou o salão desativado antes da
        execução da task Celery, o worker revalida no banco e aborta o envio registrando
        status 'ignorado_inativo'.
        """
        tz = timezone.get_current_timezone()
        appt = SchedulingService.create_appointment(
            salon=self.salon,
            client=self.client_obj,
            professional=self.prof,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 14, 0), tz),
            services=[self.service],
        )

        # Cancela o agendamento antes da task de lembrete rodar
        SchedulingService.transition_status(
            appointment=appt,
            new_status=AppointmentStatusChoices.CANCELLED,
            cancellation_reason='Cliente desistiu',
        )

        result = send_appointment_notification_task.delay(
            self.salon.pk,
            appt.pk,
            NotificationTypeChoices.REMINDER,
            'window-cancelled-check',
        ).get()
        self.assertFalse(result['sent'])
        self.assertEqual(result['status'], NotificationStatusChoices.SKIPPED_INACTIVE)
        self.assertEqual(len(mail.outbox), 0)

        # Porém o aviso de cancelamento para um agendamento cancelado é permitido e idempotente
        cancel_res_1 = send_appointment_notification_task.delay(
            self.salon.pk,
            appt.pk,
            NotificationTypeChoices.CANCELLATION,
            'cancel-v1',
        ).get()
        self.assertTrue(cancel_res_1['sent'])
        self.assertEqual(len(mail.outbox), 1)

        # Se o salão for desativado, qualquer nova notificação é abortada com segurança
        self.salon.is_active = False
        self.salon.save(update_fields=['is_active'])
        inactive_log, sent = NotificationService.dispatch_appointment_notification(
            salon_id=self.salon.pk,
            appointment_id=appt.pk,
            notification_type=NotificationTypeChoices.CANCELLATION,
            reference_window='cancel-after-salon-deactivated',
        )
        self.assertFalse(sent)
        self.assertEqual(
            inactive_log.status,
            NotificationStatusChoices.SKIPPED_INACTIVE,
        )
        self.assertEqual(len(mail.outbox), 1)
