from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from accounts.models import User, UserRoleChoices
from clients.models import Client
from salons.models import Salon


@override_settings(SECURE_SSL_REDIRECT=False)
class ClientModelAndIsolationTests(TestCase):
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
        self.prof_a = User.objects.create_user(
            email='prof@alpha.com',
            password='StrongPassword123!',
            full_name='Profissional Alpha',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon_a,
        )
        self.recep_b = User.objects.create_user(
            email='recep@beta.com',
            password='StrongPassword123!',
            full_name='Recepção Beta',
            role=UserRoleChoices.RECEPCIONISTA,
            salon=self.salon_b,
        )

        self.client_joao_a = Client(
            salon=self.salon_a,
            full_name='João da Silva',
            phone='(11) 98888-7777',
            email='joao@cliente.com',
            cpf_cnpj='123.456.789-01',
            address_street='Rua Augusta',
            address_number='500',
            address_neighborhood='Consolação',
            address_city='São Paulo',
            address_state='sp',
            address_zip_code='01305-000',
            ibge_city_code='3550308',
            notes='Alergia a amônia.',
        )
        self.client_joao_a.full_clean()
        self.client_joao_a.save()

    def test_client_normalization_and_uniqueness_scoped_per_salon(self):
        """RF-004, DEC-002: Normaliza telefone/CPF/CEP/UF e garante unicidade apenas dentro do mesmo salão."""
        self.assertEqual(self.client_joao_a.phone, '11988887777')
        self.assertEqual(self.client_joao_a.cpf_cnpj, '12345678901')
        self.assertEqual(self.client_joao_a.address_zip_code, '01305000')
        self.assertEqual(self.client_joao_a.address_state, 'SP')

        # Mesmo telefone ou CPF no Salão A deve falhar
        dup_same_salon = Client(
            salon=self.salon_a,
            full_name='João Duplicado',
            phone='11988887777',
            cpf_cnpj='12345678901',
        )
        with self.assertRaises(ValidationError) as ctx:
            dup_same_salon.full_clean()
        self.assertIn('phone', ctx.exception.message_dict)
        self.assertIn('cpf_cnpj', ctx.exception.message_dict)

        # Mesmo telefone e CPF no Salão B é permitido (carteiras isoladas por salão)
        client_same_person_salon_b = Client(
            salon=self.salon_b,
            full_name='João da Silva',
            phone='(11) 98888-7777',
            cpf_cnpj='123.456.789-01',
        )
        client_same_person_salon_b.full_clean()
        client_same_person_salon_b.save()
        self.assertEqual(Client.objects.for_salon(self.salon_b).count(), 1)

    def test_client_search_detail_and_cross_tenant_isolation(self):
        """RF-004, SEC-A, SEC-B, SEC-C: Operador do Salão B não encontra João do Salão A; profissional recebe 403."""
        # Recepcionista do Salão A busca por João e acessa ficha com aba de histórico
        self.client.force_login(self.recep_a)
        resp_search_a = self.client.get(reverse('clients:client_list'), {'q': 'João'})
        self.assertEqual(resp_search_a.status_code, 200)
        self.assertContains(resp_search_a, 'João da Silva')

        resp_detail_a = self.client.get(
            reverse('clients:client_detail', args=[self.client_joao_a.pk])
        )
        self.assertEqual(resp_detail_a.status_code, 200)
        self.assertContains(resp_detail_a, 'Alergia a amônia.')
        self.assertContains(resp_detail_a, 'Aba de Histórico de Atendimentos e Comandas')

        # Critério de aceite RF-004 / SEC-B: Operador do Salão B busca por João e não vê dados do Salão A
        self.client.force_login(self.recep_b)
        resp_search_b = self.client.get(reverse('clients:client_list'), {'q': 'João'})
        self.assertEqual(resp_search_b.status_code, 200)
        self.assertNotContains(resp_search_b, 'João da Silva')

        # Tentativa de acessar detalhe ou edição do cliente do Salão A pelo operador do Salão B -> 404
        self.assertEqual(
            self.client.get(
                reverse('clients:client_detail', args=[self.client_joao_a.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse('clients:client_edit', args=[self.client_joao_a.pk])
            ).status_code,
            404,
        )

        # SEC-C: Profissional não acessa listagem global ou cadastro de clientes -> 403
        self.client.force_login(self.prof_a)
        self.assertEqual(
            self.client.get(reverse('clients:client_list')).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse('clients:client_create')).status_code,
            403,
        )
