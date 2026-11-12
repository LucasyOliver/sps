from datetime import date, time
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from accounts.models import UserRoleChoices
from salons.models import Salon, SalonBusinessHours, SalonHoliday, TaxRegimeChoices, WeekdayChoices

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class SalonModelAndIsolationTests(TestCase):
    def setUp(self):
        self.salon_a = Salon.objects.create(
            name='Studio Beleza Pura LTDA',
            trade_name='Studio Beleza Pura',
            slug='studio-beleza-pura',
            cancellation_min_hours=2,
        )
        self.salon_b = Salon.objects.create(
            name='Barbearia Imperial LTDA',
            trade_name='Barbearia Imperial',
            slug='barbearia-imperial',
            cancellation_min_hours=3,
        )
        self.gestor_a = User.objects.create_user(
            email='gestor@belezapura.com.br',
            password='StrongPassword123!',
            full_name='Gestor A',
            role=UserRoleChoices.GESTOR,
            salon=self.salon_a,
        )
        self.recepcao_a = User.objects.create_user(
            email='recepcao@belezapura.com.br',
            password='StrongPassword123!',
            full_name='Recepção A',
            role=UserRoleChoices.RECEPCIONISTA,
            salon=self.salon_a,
        )
        self.profissional_a = User.objects.create_user(
            email='prof@belezapura.com.br',
            password='StrongPassword123!',
            full_name='Profissional A',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_a,
        )

    def test_create_salon_with_operational_and_fiscal_fields(self):
        self.salon_a.cnpj = '12.345.678/0001-99'
        self.salon_a.municipal_registration = '987654'
        self.salon_a.tax_regime = TaxRegimeChoices.SIMPLES_NACIONAL
        self.salon_a.is_partner_salon_regime = True
        self.salon_a.ibge_city_code = '3550308'
        self.salon_a.full_clean()
        self.salon_a.save()

        self.assertEqual(self.salon_a.cnpj, '12345678000199')
        self.assertEqual(self.salon_a.ibge_city_code, '3550308')
        self.assertTrue(self.salon_a.is_partner_salon_regime)

    def test_invalid_cnpj_and_ibge_raise_validation_error(self):
        salon = Salon(
            name='Salao Invalido',
            trade_name='Salao Invalido',
            slug='salao-invalido',
            cnpj='12345',
            ibge_city_code='123',
        )
        with self.assertRaises(ValidationError) as ctx:
            salon.full_clean()
        self.assertIn('cnpj', ctx.exception.message_dict)
        self.assertIn('ibge_city_code', ctx.exception.message_dict)

    def test_business_hours_and_holiday_validation(self):
        invalid_hours = SalonBusinessHours(
            salon=self.salon_a,
            weekday=WeekdayChoices.MONDAY,
            is_open=True,
            opening_time=time(18, 0),
            closing_time=time(9, 0),
        )
        with self.assertRaises(ValidationError):
            invalid_hours.full_clean()

        valid_hours = SalonBusinessHours(
            salon=self.salon_a,
            weekday=WeekdayChoices.MONDAY,
            is_open=True,
            opening_time=time(9, 0),
            closing_time=time(19, 0),
        )
        valid_hours.full_clean()
        valid_hours.save()
        self.assertEqual(SalonBusinessHours.objects.for_salon(self.salon_a).count(), 1)
        self.assertEqual(SalonBusinessHours.objects.for_salon(self.salon_b).count(), 0)

        holiday = SalonHoliday(
            salon=self.salon_a,
            date=date(2026, 12, 25),
            description='Natal',
            is_closed_all_day=True,
        )
        holiday.full_clean()
        holiday.save()
        self.assertEqual(SalonHoliday.objects.for_salon(self.salon_a).count(), 1)

    def test_gestor_can_update_own_salon_settings_and_fiscal_data(self):
        self.client.force_login(self.gestor_a)
        response = self.client.post(
            reverse('salons:settings'),
            {
                'trade_name': 'Studio Beleza Pura Prime',
                'name': 'Studio Beleza Pura LTDA',
                'phone': '11988887777',
                'email': 'financeiro@belezapura.com.br',
                'cancellation_min_hours': 4,
                'cnpj': '11.222.333/0001-44',
                'municipal_registration': '112233',
                'state_registration': '',
                'tax_regime': TaxRegimeChoices.SIMPLES_NACIONAL,
                'is_partner_salon_regime': True,
                'ibge_city_code': '3550308',
                'address_street': 'Av. Paulista',
                'address_number': '1000',
                'address_complement': 'Conj 12',
                'address_neighborhood': 'Bela Vista',
                'address_city': 'São Paulo',
                'address_state': 'SP',
                'address_zip_code': '01310100',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.salon_a.refresh_from_db()
        self.assertEqual(self.salon_a.cancellation_min_hours, 4)
        self.assertEqual(self.salon_a.cnpj, '11222333000144')
        self.assertTrue(self.salon_a.is_partner_salon_regime)

    def test_gestor_cannot_edit_other_salon_settings_cross_tenant(self):
        self.client.force_login(self.gestor_a)
        response = self.client.post(
            reverse('salons:settings_by_pk', kwargs={'pk': self.salon_b.pk}),
            {
                'trade_name': 'Tentativa Invasao',
                'name': 'Tentativa Invasao',
                'cancellation_min_hours': 10,
                'tax_regime': TaxRegimeChoices.MEI,
            },
        )
        self.assertEqual(response.status_code, 404)
        self.salon_b.refresh_from_db()
        self.assertEqual(self.salon_b.trade_name, 'Barbearia Imperial')

    def test_recepcionista_and_profissional_receive_403_on_salon_settings_and_hours_write(self):
        for member in (self.recepcao_a, self.profissional_a):
            with self.subTest(role=member.role):
                self.client.force_login(member)
                resp_settings = self.client.get(reverse('salons:settings'))
                self.assertEqual(resp_settings.status_code, 403)

                resp_hours = self.client.post(
                    reverse('salons:business_hours_save'),
                    {
                        'weekday': WeekdayChoices.TUESDAY,
                        'is_open': True,
                        'opening_time': '09:00',
                        'closing_time': '18:00',
                    },
                )
                self.assertEqual(resp_hours.status_code, 403)
