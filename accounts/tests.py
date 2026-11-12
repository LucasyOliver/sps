from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from accounts.models import UserRoleChoices
from salons.models import Salon

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class AccountsAndTenantBindingTests(TestCase):
    def setUp(self):
        self.salon = Salon.objects.create(
            name='Salão Elegance LTDA',
            trade_name='Salão Elegance',
            slug='salao-elegance',
        )
        self.other_salon = Salon.objects.create(
            name='Studio Outro Salão LTDA',
            trade_name='Studio Outro Salão',
            slug='studio-outro-salao',
        )
        self.gestor = User.objects.create_user(
            email='gestor@elegance.com.br',
            password='StrongPassword123!',
            full_name='Mariana Gestora',
            role=UserRoleChoices.GESTOR,
            salon=self.salon,
        )
        self.recepcao = User.objects.create_user(
            email='recepcao@elegance.com.br',
            password='StrongPassword123!',
            full_name='Clara Recepção',
            role=UserRoleChoices.RECEPCIONISTA,
            salon=self.salon,
        )
        self.other_member = User.objects.create_user(
            email='prof@outro.com.br',
            password='StrongPassword123!',
            full_name='Roberto Outro Salão',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.other_salon,
        )

    def test_internal_user_requires_fixed_salon_binding(self):
        for role in (
            UserRoleChoices.GESTOR,
            UserRoleChoices.RECEPCIONISTA,
            UserRoleChoices.PROFISSIONAL,
        ):
            with self.subTest(role=role):
                with self.assertRaises(ValidationError) as ctx:
                    User.objects.create_user(
                        email=f'{role}_sem_salao@elegance.com.br',
                        password='StrongPassword123!',
                        full_name=f'Colaborador {role}',
                        role=role,
                        salon=None,
                    )
                self.assertIn('salon', ctx.exception.message_dict)

    def test_create_salon_member_and_normalize_email(self):
        user = User.objects.create_user(
            email='NovoProf@Elegance.com.br',
            password='StrongPassword123!',
            full_name='Lucas Especialista',
            role=UserRoleChoices.PROFISSIONAL,
            salon=self.salon,
        )
        self.assertEqual(user.email, 'novoprof@elegance.com.br')
        self.assertEqual(user.salon, self.salon)
        self.assertTrue(user.is_salon_member)

    def test_create_superuser_saas_without_salon_succeeds(self):
        admin_user = User.objects.create_superuser(
            email='admin@sps.com.br',
            password='SuperSecretPassword123!',
            full_name='Superadmin SPS',
        )
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_staff)
        self.assertEqual(admin_user.role, UserRoleChoices.SUPERADMIN_SAAS)
        self.assertIsNone(admin_user.salon)

    def test_email_login_and_authenticated_home_view(self):
        unauth_response = self.client.get(reverse('base:home'))
        self.assertEqual(unauth_response.status_code, 302)

        login_response = self.client.post(
            reverse('accounts:login'),
            {'username': 'recepcao@elegance.com.br', 'password': 'StrongPassword123!'},
            follow=True,
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, 'Salão Elegance')
        self.assertContains(login_response, 'Clara Recepção')

    def test_gestor_creates_team_member_bound_to_own_salon_and_isolates_list(self):
        self.client.force_login(self.gestor)
        list_resp = self.client.get(reverse('accounts:team_list'))
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, 'Clara Recepção')
        self.assertNotContains(list_resp, 'Roberto Outro Salão')

        create_resp = self.client.post(
            reverse('accounts:team_create'),
            {
                'email': 'ana.parceira@elegance.com.br',
                'full_name': 'Ana Cabeleireira',
                'phone': '11977776666',
                'role': UserRoleChoices.PROFISSIONAL,
                'tax_document': '12345678901',
                'is_active': True,
                'password1': 'SenhaForte123!',
                'password2': 'SenhaForte123!',
            },
        )
        self.assertEqual(create_resp.status_code, 302)
        ana = User.objects.get(email='ana.parceira@elegance.com.br')
        self.assertEqual(ana.salon, self.salon)
        self.assertEqual(ana.tax_document, '12345678901')

    def test_gestor_cannot_edit_team_member_from_other_salon(self):
        self.client.force_login(self.gestor)
        resp = self.client.get(
            reverse('accounts:team_update', kwargs={'pk': self.other_member.pk})
        )
        self.assertEqual(resp.status_code, 404)

    def test_non_gestor_cannot_access_team_management(self):
        self.client.force_login(self.recepcao)
        self.assertEqual(self.client.get(reverse('accounts:team_list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('accounts:team_create')).status_code, 403)
