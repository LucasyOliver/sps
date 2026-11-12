from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from accounts.models import User, UserRoleChoices
from catalog.forms import ProfessionalServiceCommissionForm, ServiceForm
from catalog.models import ProfessionalServiceCommission, Service, ServiceCategory
from catalog.services import (
    calculate_commission_amount,
    resolve_commission_percentage,
)
from salons.models import Salon


@override_settings(SECURE_SSL_REDIRECT=False)
class CatalogAndCommissionTests(TestCase):
    def setUp(self):
        self.salon_a = Salon.objects.create(
            name='Salão Alpha Beleza Ltda',
            trade_name='Salão Alpha',
            slug='salao-alpha',
        )
        self.salon_b = Salon.objects.create(
            name='Salão Beta Estética Ltda',
            trade_name='Salão Beta',
            slug='salao-beta',
        )

        self.gestor_a = User.objects.create_user(
            email='gestor@alpha.com',
            password='StrongPassword123!',
            full_name='Gestor Alpha',
            role=UserRoleChoices.GESTOR,
            salon=self.salon_a,
        )
        self.recep_a = User.objects.create_user(
            email='recep@alpha.com',
            password='StrongPassword123!',
            full_name='Recepção Alpha',
            role=UserRoleChoices.RECEPCIONISTA,
            salon=self.salon_a,
        )
        self.prof_ana = User.objects.create_user(
            email='ana@alpha.com',
            password='StrongPassword123!',
            full_name='Ana Cabeleireira',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_a,
        )
        self.prof_bruno = User.objects.create_user(
            email='bruno@alpha.com',
            password='StrongPassword123!',
            full_name='Bruno Barbeiro',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_a,
        )
        self.prof_beta = User.objects.create_user(
            email='carla@beta.com',
            password='StrongPassword123!',
            full_name='Carla Beta',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_b,
        )

        self.cat_a = ServiceCategory.objects.create(
            salon=self.salon_a,
            name='Cabelos',
            description='Cortes, escovas e tratamentos capilares',
        )
        self.cat_b = ServiceCategory.objects.create(
            salon=self.salon_b,
            name='Estética Facial',
        )

        self.service_corte_escova = Service.objects.create(
            salon=self.salon_a,
            category=self.cat_a,
            name='Corte + Escova',
            duration_minutes=60,
            base_price=Decimal('100.00'),
            default_commission_pct=Decimal('40.00'),
            lc116_service_code='06.01',
            cnae_code='9602-5/01',
            iss_rate_pct=Decimal('5.00'),
        )
        self.service_corte_escova.professionals.add(self.prof_ana, self.prof_bruno)

        self.service_beta = Service.objects.create(
            salon=self.salon_b,
            category=self.cat_b,
            name='Limpeza de Pele',
            duration_minutes=45,
            base_price=Decimal('150.00'),
            default_commission_pct=Decimal('35.00'),
        )

    def test_resolve_commission_percentage_precedence_and_amount(self):
        """RF-003: Regra específica (50% para Ana) prevalece sobre comissão padrão (40%)."""
        rule_ana = ProfessionalServiceCommission.objects.create(
            salon=self.salon_a,
            professional=self.prof_ana,
            service=self.service_corte_escova,
            commission_pct=Decimal('50.00'),
        )

        pct_ana = resolve_commission_percentage(
            self.salon_a, self.prof_ana, self.service_corte_escova
        )
        pct_bruno = resolve_commission_percentage(
            self.salon_a, self.prof_bruno, self.service_corte_escova
        )

        self.assertEqual(pct_ana, Decimal('50.00'))
        self.assertEqual(pct_bruno, Decimal('40.00'))
        self.assertEqual(
            calculate_commission_amount(Decimal('100.00'), pct_ana),
            Decimal('50.00'),
        )
        self.assertEqual(
            calculate_commission_amount(Decimal('100.00'), pct_bruno),
            Decimal('40.00'),
        )

        # Desativando a regra específica de Ana, volta para o padrão do serviço (40%)
        rule_ana.is_active = False
        rule_ana.save()
        self.assertEqual(
            resolve_commission_percentage(
                self.salon_a, self.prof_ana, self.service_corte_escova
            ),
            Decimal('40.00'),
        )

        # Cruzamento entre salões deve lançar ValidationError
        with self.assertRaises(ValidationError):
            resolve_commission_percentage(
                self.salon_a, self.prof_beta, self.service_corte_escova
            )

    def test_service_and_commission_views_permissions_and_cross_tenant_isolation(self):
        """SEC-A, SEC-B, SEC-C: Gestor gerencia catálogo; recepção/profissional apenas leem; isolamento 404."""
        rule_ana = ProfessionalServiceCommission.objects.create(
            salon=self.salon_a,
            professional=self.prof_ana,
            service=self.service_corte_escova,
            commission_pct=Decimal('50.00'),
        )
        rule_bruno = ProfessionalServiceCommission.objects.create(
            salon=self.salon_a,
            professional=self.prof_bruno,
            service=self.service_corte_escova,
            commission_pct=Decimal('45.00'),
        )
        rule_beta = ProfessionalServiceCommission.objects.create(
            salon=self.salon_b,
            professional=self.prof_beta,
            service=self.service_beta,
            commission_pct=Decimal('60.00'),
        )

        # Gestor Alpha lista apenas serviços do Salão Alpha e cria novo serviço
        self.client.force_login(self.gestor_a)
        resp_list = self.client.get(reverse('catalog:service_list'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, 'Corte + Escova')
        self.assertNotContains(resp_list, 'Limpeza de Pele')

        resp_create = self.client.post(
            reverse('catalog:service_create'),
            {
                'category': self.cat_a.pk,
                'name': 'Hidratação Profunda',
                'description': 'Tratamento com máscara nutritiva',
                'duration_minutes': 45,
                'base_price': '120.00',
                'default_commission_pct': '35.00',
                'professionals': [self.prof_ana.pk],
                'lc116_service_code': '06.01',
                'cnae_code': '9602-5/01',
                'iss_rate_pct': '3.50',
                'is_active': True,
            },
        )
        self.assertEqual(resp_create.status_code, 302)
        self.assertTrue(
            Service.objects.for_salon(self.salon_a)
            .filter(name='Hidratação Profunda')
            .exists()
        )

        # SEC-B: Gestor Alpha tenta editar serviço ou regra de comissão do Salão Beta -> 404
        self.assertEqual(
            self.client.get(
                reverse('catalog:service_edit', args=[self.service_beta.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse('catalog:commission_rule_edit', args=[rule_beta.pk])
            ).status_code,
            404,
        )

        # SEC-C: Recepcionista pode listar serviços, mas recebe 403 ao tentar criar/editar serviço ou comissão
        self.client.force_login(self.recep_a)
        self.assertEqual(
            self.client.get(reverse('catalog:service_list')).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse('catalog:service_create')).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse('catalog:commission_rule_create')).status_code,
            403,
        )

        # SEC-C: Profissional Ana vê apenas a própria regra de comissão na listagem e recebe 403 na criação
        self.client.force_login(self.prof_ana)
        resp_comm_ana = self.client.get(reverse('catalog:commission_rule_list'))
        self.assertEqual(resp_comm_ana.status_code, 200)
        self.assertContains(resp_comm_ana, 'Ana Cabeleireira')
        self.assertNotContains(resp_comm_ana, 'Bruno Barbeiro')
        self.assertEqual(
            self.client.get(
                reverse('catalog:commission_rule_edit', args=[rule_ana.pk])
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                reverse('catalog:commission_rule_edit', args=[rule_bruno.pk])
            ).status_code,
            403,
        )

    def test_cross_tenant_association_rejected_in_forms_and_models(self):
        """SEC-D: Impede associação de categoria, profissional ou serviço de outro salão."""
        form_service = ServiceForm(
            data={
                'category': self.cat_b.pk,
                'name': 'Serviço Inválido',
                'duration_minutes': 30,
                'base_price': '80.00',
                'default_commission_pct': '40.00',
                'professionals': [self.prof_beta.pk],
                'is_active': True,
            },
            salon=self.salon_a,
        )
        self.assertFalse(form_service.is_valid())
        self.assertIn('category', form_service.errors)
        self.assertIn('professionals', form_service.errors)

        form_comm = ProfessionalServiceCommissionForm(
            data={
                'professional': self.prof_beta.pk,
                'service': self.service_beta.pk,
                'commission_pct': '50.00',
                'is_active': True,
            },
            salon=self.salon_a,
        )
        self.assertFalse(form_comm.is_valid())
        self.assertIn('professional', form_comm.errors)
        self.assertIn('service', form_comm.errors)
