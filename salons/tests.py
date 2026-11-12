from django.core.exceptions import ValidationError
from django.test import TestCase
from salons.models import Salon, TaxRegimeChoices


class SalonModelTests(TestCase):
    def test_create_salon_with_operational_and_fiscal_fields(self):
        salon = Salon(
            name='Studio Beleza Pura LTDA',
            trade_name='Studio Beleza Pura',
            slug='studio-beleza-pura',
            phone='11999998888',
            email='contato@belezapura.com.br',
            cancellation_min_hours=4,
            cnpj='12.345.678/0001-99',
            municipal_registration='987654',
            tax_regime=TaxRegimeChoices.SIMPLES_NACIONAL,
            is_partner_salon_regime=True,
            ibge_city_code='3550308',
        )
        salon.full_clean()
        salon.save()

        self.assertEqual(salon.cnpj, '12345678000199')
        self.assertEqual(salon.ibge_city_code, '3550308')
        self.assertTrue(salon.is_partner_salon_regime)
        self.assertEqual(salon.cancellation_min_hours, 4)

    def test_invalid_cnpj_length_raises_validation_error(self):
        salon = Salon(
            name='Salao Invalido',
            trade_name='Salao Invalido',
            slug='salao-invalido',
            cnpj='12345',
        )
        with self.assertRaises(ValidationError) as ctx:
            salon.full_clean()
        self.assertIn('cnpj', ctx.exception.message_dict)

    def test_invalid_ibge_city_code_raises_validation_error(self):
        salon = Salon(
            name='Salao IBGE Invalido',
            trade_name='Salao IBGE Invalido',
            slug='salao-ibge-invalido',
            ibge_city_code='123',
        )
        with self.assertRaises(ValidationError) as ctx:
            salon.full_clean()
        self.assertIn('ibge_city_code', ctx.exception.message_dict)
