from datetime import datetime, time
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from accounts.models import UserRoleChoices
from salons.models import Salon, SalonBusinessHours, WeekdayChoices
from scheduling.models import (
    ProfessionalSchedule,
    ScheduleBlock,
    ScheduleBlockTypeChoices,
)

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
        self.prof_a1 = User.objects.create_user(
            email='ana@alpha.com.br',
            password='StrongPassword123!',
            full_name='Ana Especialista',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_a,
        )
        self.prof_a2 = User.objects.create_user(
            email='bia@alpha.com.br',
            password='StrongPassword123!',
            full_name='Bia Especialista',
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

        valid_schedule = ProfessionalSchedule(
            salon=self.salon_a,
            professional=self.prof_a1,
            weekday=WeekdayChoices.MONDAY,
            is_working=True,
            start_time=time(9, 0),
            end_time=time(18, 0),
            break_start_time=time(12, 0),
            break_end_time=time(13, 0),
        )
        valid_schedule.full_clean()
        valid_schedule.save()
        self.assertEqual(ProfessionalSchedule.objects.for_salon(self.salon_a).count(), 1)

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

        # Profissional A1 vê apenas o próprio bloqueio e recebe 404 ao tentar excluir bloqueio de A2
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
