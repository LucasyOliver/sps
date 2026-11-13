from datetime import date, datetime, time, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from accounts.models import UserRoleChoices
from catalog.models import Service, ServiceCategory
from clients.models import Client
from salons.models import Salon, SalonBusinessHours, SalonHoliday, WeekdayChoices
from scheduling.forms import AppointmentCreateForm
from scheduling.models import (
    Appointment,
    AppointmentStatusChoices,
    ProfessionalSchedule,
    ScheduleBlock,
    ScheduleBlockTypeChoices,
)
from scheduling.services import AvailabilityService, SchedulingService

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class ProfessionalScheduleAndBlockTests(TestCase):
    def setUp(self):
        self.salon_a = Salon.objects.create(
            name='Salão Alpha LTDA',
            trade_name='Salão Alpha',
            slug='salao-alpha',
        )
        self.salon_b = Salon.objects.create(
            name='Salão Beta LTDA',
            trade_name='Salão Beta',
            slug='salao-beta',
        )
        SalonBusinessHours.objects.create(
            salon=self.salon_a,
            weekday=WeekdayChoices.MONDAY,
            is_open=True,
            opening_time=time(9, 0),
            closing_time=time(19, 0),
        )
        SalonBusinessHours.objects.create(
            salon=self.salon_a,
            weekday=WeekdayChoices.SUNDAY,
            is_open=False,
        )

        self.gestor_a = User.objects.create_user(
            email='gestor@alpha.com.br',
            password='StrongPassword123!',
            full_name='Gestor Alpha',
            role=UserRoleChoices.GESTOR,
            salon=self.salon_a,
        )
        self.recep_a = User.objects.create_user(
            email='recep@alpha.com.br',
            password='StrongPassword123!',
            full_name='Recepção Alpha',
            role=UserRoleChoices.RECEPCIONISTA,
            salon=self.salon_a,
        )
        self.prof_a1 = User.objects.create_user(
            email='ana@alpha.com.br',
            password='StrongPassword123!',
            full_name='Ana Especialista',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_a,
        )
        self.prof_a2 = User.objects.create_user(
            email='carlos@alpha.com.br',
            password='StrongPassword123!',
            full_name='Carlos Especialista',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_a,
        )
        self.prof_b = User.objects.create_user(
            email='carlos@beta.com.br',
            password='StrongPassword123!',
            full_name='Carlos Beta',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_b,
        )

        ProfessionalSchedule.objects.create(
            salon=self.salon_a,
            professional=self.prof_a2,
            weekday=WeekdayChoices.MONDAY,
            is_working=True,
            start_time=time(9, 0),
            end_time=time(18, 0),
            break_start_time=time(12, 0),
            break_end_time=time(13, 0),
        )
        ProfessionalSchedule.objects.create(
            salon=self.salon_a,
            professional=self.prof_a1,
            weekday=WeekdayChoices.MONDAY,
            is_working=True,
            start_time=time(9, 0),
            end_time=time(18, 0),
        )

        self.cat_a = ServiceCategory.objects.create(
            salon=self.salon_a,
            name='Barbearia e Cabelo',
        )
        self.srv_30m = Service.objects.create(
            salon=self.salon_a,
            category=self.cat_a,
            name='Corte Masculino',
            duration_minutes=30,
            base_price=Decimal('50.00'),
            default_commission_pct=Decimal('40.00'),
        )
        self.srv_30m.professionals.add(self.prof_a1, self.prof_a2)

        self.srv_45m = Service.objects.create(
            salon=self.salon_a,
            category=self.cat_a,
            name='Barba Completa + Hidratação',
            duration_minutes=45,
            base_price=Decimal('70.00'),
            default_commission_pct=Decimal('45.00'),
        )
        self.srv_45m.professionals.add(self.prof_a2)

        self.srv_b = Service.objects.create(
            salon=self.salon_b,
            name='Serviço Beta',
            duration_minutes=30,
            base_price=Decimal('60.00'),
        )

        self.client_a = Client.objects.create(
            salon=self.salon_a,
            full_name='Cliente Maria',
            phone='11977776666',
        )
        self.client_b = Client.objects.create(
            salon=self.salon_b,
            full_name='Cliente Beta',
            phone='11955554444',
        )

    def test_professional_schedule_must_fit_within_salon_business_hours(self):
        outside_hours = ProfessionalSchedule(
            salon=self.salon_a,
            professional=self.prof_a1,
            weekday=WeekdayChoices.MONDAY,
            is_working=True,
            start_time=time(8, 0),
            end_time=time(18, 0),
        )
        with self.assertRaises(ValidationError):
            outside_hours.full_clean()

        closed_day_schedule = ProfessionalSchedule(
            salon=self.salon_a,
            professional=self.prof_a1,
            weekday=WeekdayChoices.SUNDAY,
            is_working=True,
            start_time=time(10, 0),
            end_time=time(14, 0),
        )
        with self.assertRaises(ValidationError):
            closed_day_schedule.full_clean()

    def test_cross_tenant_professional_assignment_is_rejected(self):
        cross_schedule = ProfessionalSchedule(
            salon=self.salon_a,
            professional=self.prof_b,
            weekday=WeekdayChoices.MONDAY,
            is_working=True,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        with self.assertRaises(ValidationError) as ctx:
            cross_schedule.full_clean()
        self.assertIn('professional', ctx.exception.message_dict)

    def test_schedule_block_overlaps_and_professional_scope_isolation(self):
        tz = timezone.get_current_timezone()
        block_a1 = ScheduleBlock.objects.create(
            salon=self.salon_a,
            professional=self.prof_a1,
            block_type=ScheduleBlockTypeChoices.ABSENCE,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 12, 0), tz),
            end_at=timezone.make_aware(datetime(2026, 11, 16, 13, 0), tz),
            reason='Consulta médica',
            created_by=self.prof_a1,
        )
        block_a2 = ScheduleBlock.objects.create(
            salon=self.salon_a,
            professional=self.prof_a2,
            block_type=ScheduleBlockTypeChoices.DAY_OFF,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 14, 0), tz),
            end_at=timezone.make_aware(datetime(2026, 11, 16, 18, 0), tz),
            reason='Folga tarde',
            created_by=self.gestor_a,
        )

        self.assertTrue(
            block_a1.overlaps(
                timezone.make_aware(datetime(2026, 11, 16, 12, 30), tz),
                timezone.make_aware(datetime(2026, 11, 16, 13, 30), tz),
            )
        )
        self.assertFalse(
            block_a1.overlaps(
                timezone.make_aware(datetime(2026, 11, 16, 13, 0), tz),
                timezone.make_aware(datetime(2026, 11, 16, 14, 0), tz),
            )
        )

        self.client.force_login(self.prof_a1)
        list_resp = self.client.get(reverse('scheduling:schedule_blocks'))
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, 'Consulta médica')
        self.assertNotContains(list_resp, 'Folga tarde')

        delete_other_resp = self.client.post(
            reverse('scheduling:schedule_block_delete', kwargs={'pk': block_a2.pk})
        )
        self.assertEqual(delete_other_resp.status_code, 404)
        self.assertTrue(ScheduleBlock.objects.filter(pk=block_a2.pk).exists())

    def test_multi_service_duration_sum_and_double_booking_rejection(self):
        """
        RF-005 Critério de aceite: 2 serviços (30m + 45m = 75m) agendados às 14:00 para Carlos
        reservam das 14:00 às 15:15; tentativa concorrente às 15:00 é rejeitada.
        """
        tz = timezone.get_current_timezone()
        monday_14h = timezone.make_aware(datetime(2026, 11, 16, 14, 0), tz)

        appt = SchedulingService.create_appointment(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a2,
            start_at=monday_14h,
            services=[self.srv_30m, self.srv_45m],
            created_by=self.recep_a,
        )

        self.assertEqual(appt.total_duration_minutes, 75)
        self.assertEqual(appt.total_estimated_amount, Decimal('120.00'))
        self.assertEqual(
            timezone.localtime(appt.end_at, tz),
            timezone.make_aware(datetime(2026, 11, 16, 15, 15), tz),
        )
        self.assertEqual(appt.items.count(), 2)

        # Tentativa de agendar Carlos às 15:00 (conflita com 14:00..15:15) -> ValidationError
        monday_15h = timezone.make_aware(datetime(2026, 11, 16, 15, 0), tz)
        with self.assertRaises(ValidationError):
            SchedulingService.create_appointment(
                salon=self.salon_a,
                client=self.client_a,
                professional=self.prof_a2,
                start_at=monday_15h,
                services=[self.srv_30m],
            )

        # Agendar exatamente às 15:15 (após término) deve ser permitido
        monday_15h15 = timezone.make_aware(datetime(2026, 11, 16, 15, 15), tz)
        appt_after = SchedulingService.create_appointment(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a2,
            start_at=monday_15h15,
            services=[self.srv_30m],
        )
        self.assertEqual(appt_after.total_duration_minutes, 30)

    def test_availability_service_respects_breaks_blocks_and_holidays(self):
        """S04-T02: AvailabilityService bloqueia intervalo de almoço, ScheduleBlock e feriado."""
        tz = timezone.get_current_timezone()
        target_monday = date(2026, 11, 16)

        # Bloqueio das 16:00 às 17:00 para Carlos
        ScheduleBlock.objects.create(
            salon=self.salon_a,
            professional=self.prof_a2,
            block_type=ScheduleBlockTypeChoices.ABSENCE,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 16, 0), tz),
            end_at=timezone.make_aware(datetime(2026, 11, 16, 17, 0), tz),
            reason='Saída externa',
        )

        # Tentativa no horário de almoço de Carlos (12:00 às 13:00) -> rejeitada
        with self.assertRaises(ValidationError):
            SchedulingService.create_appointment(
                salon=self.salon_a,
                client=self.client_a,
                professional=self.prof_a2,
                start_at=timezone.make_aware(datetime(2026, 11, 16, 12, 15), tz),
                services=[self.srv_30m],
            )

        # Tentativa no bloqueio de agenda (16:00 às 17:00) -> rejeitada
        with self.assertRaises(ValidationError):
            SchedulingService.create_appointment(
                salon=self.salon_a,
                client=self.client_a,
                professional=self.prof_a2,
                start_at=timezone.make_aware(datetime(2026, 11, 16, 16, 0), tz),
                services=[self.srv_30m],
            )

        slots = AvailabilityService.get_available_slots(
            salon=self.salon_a,
            professional=self.prof_a2,
            target_date=target_monday,
            services=[self.srv_30m],
            slot_step_minutes=30,
        )
        slot_times = [timezone.localtime(s, tz).time() for s in slots]
        self.assertIn(time(9, 0), slot_times)
        self.assertNotIn(time(12, 0), slot_times)
        self.assertNotIn(time(12, 30), slot_times)
        self.assertNotIn(time(16, 0), slot_times)
        self.assertNotIn(time(16, 30), slot_times)
        self.assertIn(time(17, 0), slot_times)

        # Cadastrando feriado na segunda-feira -> zero slots disponíveis
        SalonHoliday.objects.create(
            salon=self.salon_a,
            date=target_monday,
            description='Feriado Municipal',
            is_closed_all_day=True,
        )
        self.assertEqual(
            AvailabilityService.get_available_slots(
                salon=self.salon_a,
                professional=self.prof_a2,
                target_date=target_monday,
                services=[self.srv_30m],
            ),
            [],
        )

    def test_status_transitions_cancellation_reason_and_reschedule(self):
        """S04-T03: Testa ciclo de vida de status, obrigatoriedade de motivo ao cancelar e remarcação."""
        tz = timezone.get_current_timezone()
        appt = SchedulingService.create_appointment(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a2,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 9, 0), tz),
            services=[self.srv_30m],
        )

        # Remarcar para 10:00
        appt = SchedulingService.reschedule_appointment(
            appointment=appt,
            new_start_at=timezone.make_aware(datetime(2026, 11, 16, 10, 0), tz),
        )
        self.assertEqual(timezone.localtime(appt.start_at, tz).time(), time(10, 0))

        # Cancelar sem motivo deve falhar
        with self.assertRaises(ValidationError):
            SchedulingService.transition_status(
                appointment=appt,
                new_status=AppointmentStatusChoices.CANCELLED,
                cancellation_reason='',
            )

        # Transições válidas: agendado -> confirmado -> em_atendimento -> concluido
        appt = SchedulingService.transition_status(
            appointment=appt,
            new_status=AppointmentStatusChoices.CONFIRMED,
        )
        appt = SchedulingService.transition_status(
            appointment=appt,
            new_status=AppointmentStatusChoices.IN_PROGRESS,
        )
        appt = SchedulingService.transition_status(
            appointment=appt,
            new_status=AppointmentStatusChoices.COMPLETED,
        )
        self.assertEqual(appt.status, AppointmentStatusChoices.COMPLETED)

        # Agendamento concluído não pode transicionar para cancelado
        with self.assertRaises(ValidationError):
            SchedulingService.transition_status(
                appointment=appt,
                new_status=AppointmentStatusChoices.CANCELLED,
                cancellation_reason='Tentativa inválida',
            )

    def test_agenda_views_professional_scope_and_cross_tenant_isolation(self):
        """SEC-A, SEC-B, SEC-C, SEC-D: Views da agenda respeitam escopo do profissional e isolamento multi-tenant."""
        tz = timezone.get_current_timezone()
        appt_a1 = SchedulingService.create_appointment(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a1,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 9, 0), tz),
            services=[self.srv_30m],
        )
        appt_a2 = SchedulingService.create_appointment(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a2,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 10, 0), tz),
            services=[self.srv_30m],
        )
        appt_b = Appointment.objects.create(
            salon=self.salon_b,
            client=self.client_b,
            professional=self.prof_b,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 11, 0), tz),
            end_at=timezone.make_aware(datetime(2026, 11, 16, 11, 30), tz),
            total_duration_minutes=30,
            total_estimated_amount=Decimal('60.00'),
        )

        # SEC-C: Profissional A1 vê apenas o próprio agendamento e recebe 404 no agendamento de A2
        self.client.force_login(self.prof_a1)
        resp_agenda = self.client.get(reverse('scheduling:appointment_list'))
        self.assertEqual(resp_agenda.status_code, 200)
        self.assertContains(resp_agenda, 'Ana Especialista')
        self.assertNotContains(resp_agenda, 'Carlos Especialista')

        self.assertEqual(
            self.client.get(
                reverse('scheduling:appointment_detail', args=[appt_a1.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse('scheduling:appointment_detail', args=[appt_a2.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse('scheduling:appointment_reschedule', args=[appt_a2.pk])
            ).status_code,
            404,
        )

        # SEC-B: Gestor do Salão A recebe 404 ao tentar acessar agendamento do Salão B
        self.client.force_login(self.gestor_a)
        self.assertEqual(
            self.client.get(
                reverse('scheduling:appointment_detail', args=[appt_b.pk])
            ).status_code,
            404,
        )

        # SEC-D: Formulário rejeita cliente, profissional ou serviço de outro salão
        cross_form = AppointmentCreateForm(
            data={
                'client': self.client_b.pk,
                'professional': self.prof_b.pk,
                'services': [self.srv_b.pk],
                'start_at': '2026-11-16T14:00',
            },
            salon=self.salon_a,
            actor=self.gestor_a,
        )
        self.assertFalse(cross_form.is_valid())
        self.assertIn('client', cross_form.errors)
        self.assertIn('professional', cross_form.errors)
        self.assertIn('services', cross_form.errors)

    def test_public_booking_creates_client_multi_service_appointment_and_reuses_client(self):
        """
        S05-T02 / RF-006: Portal público (/s/<slug>/) calcula horários livres reais para
        múltiplos serviços, cria/reutiliza Client isolado no salão e redireciona para o token público.
        """
        booking_url = reverse(
            'public_booking:salon_booking',
            kwargs={'salon_slug': self.salon_a.slug},
        )
        get_resp = self.client.get(
            f'{booking_url}?professional={self.prof_a2.pk}&date=2026-11-16'
            f'&services={self.srv_30m.pk}&services={self.srv_45m.pk}'
        )
        self.assertEqual(get_resp.status_code, 200)
        self.assertContains(get_resp, 'sps-design-system.css')
        self.assertContains(get_resp, 'Duração total: 75 min')
        self.assertContains(get_resp, '09:00')

        post_resp = self.client.post(
            booking_url,
            data={
                'services': [self.srv_30m.pk, self.srv_45m.pk],
                'professional': self.prof_a2.pk,
                'start_at': '2026-11-16T09:00',
                'client_full_name': 'Fernanda Lima',
                'client_phone': '(11) 98888-7777',
                'client_email': 'fernanda@cliente.com.br',
                'client_cpf_cnpj': '123.456.789-01',
                'notes': 'Primeira visita pelo portal público',
            },
        )
        self.assertEqual(post_resp.status_code, 302)

        created_client = Client.objects.for_salon(self.salon_a).get(phone='11988887777')
        self.assertEqual(created_client.full_name, 'Fernanda Lima')
        self.assertEqual(created_client.cpf_cnpj, '12345678901')

        appt = Appointment.objects.for_salon(self.salon_a).get(client=created_client)
        self.assertEqual(appt.total_duration_minutes, 75)
        self.assertEqual(appt.total_estimated_amount, Decimal('120.00'))
        self.assertEqual(
            post_resp['Location'],
            reverse(
                'public_booking:appointment_detail',
                kwargs={
                    'salon_slug': self.salon_a.slug,
                    'public_token': appt.public_token,
                },
            ),
        )

        # Novo agendamento público com o mesmo telefone reutiliza o registro Client sem erro de duplicidade
        second_resp = self.client.post(
            booking_url,
            data={
                'services': [self.srv_30m.pk],
                'professional': self.prof_a2.pk,
                'start_at': '2026-11-16T10:30',
                'client_full_name': 'Fernanda Lima Atualizada',
                'client_phone': '11988887777',
            },
        )
        self.assertEqual(second_resp.status_code, 302)
        self.assertEqual(
            Client.objects.for_salon(self.salon_a).filter(phone='11988887777').count(),
            1,
        )

    def test_public_booking_blocks_conflict_with_internal_agenda(self):
        """
        S05-T04 / RF-006: Agendamento público é bloqueado se colidir com agendamento
        já existente na agenda interna do salão.
        """
        tz = timezone.get_current_timezone()
        SchedulingService.create_appointment(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a2,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 14, 0), tz),
            services=[self.srv_30m, self.srv_45m],
            created_by=self.recep_a,
        )

        booking_url = reverse(
            'public_booking:salon_booking',
            kwargs={'salon_slug': self.salon_a.slug},
        )
        conflict_resp = self.client.post(
            booking_url,
            data={
                'services': [self.srv_30m.pk],
                'professional': self.prof_a2.pk,
                'start_at': '2026-11-16T14:30',
                'client_full_name': 'Cliente Concorrente',
                'client_phone': '11966665555',
            },
        )
        self.assertEqual(conflict_resp.status_code, 200)
        self.assertContains(conflict_resp, 'Conflito de horário')
        self.assertEqual(Appointment.objects.for_salon(self.salon_a).count(), 1)

    def test_public_cancellation_deadline_enforcement(self):
        """
        S05-T03 / S05-T04 / RF-006 Critério de aceite:
        Dado um salão com antecedência mínima de cancelamento de 3 horas e um agendamento
        às 16:00, quando o cliente tentar cancelar às 14:00 (faltando 2h), a operação é
        negada e o agendamento permanece ativo; quando cancelar dentro do prazo (<= 13:00),
        o cancelamento é efetivado.
        """
        tz = timezone.get_current_timezone()
        self.salon_a.cancellation_min_hours = 3
        self.salon_a.save(update_fields=['cancellation_min_hours'])

        appt_16h = SchedulingService.create_appointment(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a2,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 16, 0), tz),
            services=[self.srv_30m],
        )

        # Tentativa às 14:00 (apenas 2h antes das 16:00, menor que 3h exigidas) -> negada
        attempt_at_14h = timezone.make_aware(datetime(2026, 11, 16, 14, 0), tz)
        with self.assertRaises(ValidationError):
            SchedulingService.cancel_public_appointment(
                salon=self.salon_a,
                appointment=appt_16h,
                cancellation_reason='Imprevisto de última hora',
                now=attempt_at_14h,
            )
        appt_16h.refresh_from_db()
        self.assertEqual(appt_16h.status, AppointmentStatusChoices.SCHEDULED)

        # Tentativa às 12:30 (3h30 antes das 16:00, dentro do prazo de 3h) -> permitida
        attempt_at_12h30 = timezone.make_aware(datetime(2026, 11, 16, 12, 30), tz)
        SchedulingService.cancel_public_appointment(
            salon=self.salon_a,
            appointment=appt_16h,
            cancellation_reason='Reunião antecipada',
            now=attempt_at_12h30,
        )
        appt_16h.refresh_from_db()
        self.assertEqual(appt_16h.status, AppointmentStatusChoices.CANCELLED)
        self.assertEqual(appt_16h.cancellation_reason, 'Reunião antecipada')

        # Teste ponta a ponta via View HTTP com agendamento a 1 hora do início (fora do prazo de 3h)
        near_start = timezone.now() + timedelta(hours=1)
        appt_near = Appointment.objects.create(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a1,
            start_at=near_start,
            end_at=near_start + timedelta(minutes=30),
            total_duration_minutes=30,
            total_estimated_amount=Decimal('50.00'),
        )
        detail_url = reverse(
            'public_booking:appointment_detail',
            kwargs={
                'salon_slug': self.salon_a.slug,
                'public_token': appt_near.public_token,
            },
        )
        late_post = self.client.post(
            detail_url,
            data={'cancellation_reason': 'Tentativa fora do prazo via HTTP'},
        )
        self.assertEqual(late_post.status_code, 200)
        self.assertContains(late_post, 'O prazo para cancelamento online encerrou')
        appt_near.refresh_from_db()
        self.assertEqual(appt_near.status, AppointmentStatusChoices.SCHEDULED)

    def test_public_routes_enforce_tenant_isolation_and_active_salon(self):
        """
        SEC-B / RNF-001: Token público do Salão A não pode ser consultado nem cancelado
        pela rota do Salão B, e salão inativo retorna 404.
        """
        tz = timezone.get_current_timezone()
        appt_a = SchedulingService.create_appointment(
            salon=self.salon_a,
            client=self.client_a,
            professional=self.prof_a2,
            start_at=timezone.make_aware(datetime(2026, 11, 16, 11, 0), tz),
            services=[self.srv_30m],
        )

        cross_salon_url = reverse(
            'public_booking:appointment_detail',
            kwargs={
                'salon_slug': self.salon_b.slug,
                'public_token': appt_a.public_token,
            },
        )
        self.assertEqual(self.client.get(cross_salon_url).status_code, 404)
        self.assertEqual(self.client.post(cross_salon_url).status_code, 404)

        self.salon_a.is_active = False
        self.salon_a.save(update_fields=['is_active'])
        booking_a_url = reverse(
            'public_booking:salon_booking',
            kwargs={'salon_slug': self.salon_a.slug},
        )
        self.assertEqual(self.client.get(booking_a_url).status_code, 404)
