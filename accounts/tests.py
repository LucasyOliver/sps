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

    def test_internal_user_requires_fixed_salon_binding(self):
        for role in (
            UserRoleChoices.GESTOR,
            UserRoleChoices.RECEPCIONISTA,
            UserRoleChoices.PROFISSIONAL,
        ):
            with self.subTest(role=role):
                with self.assertRaises(ValidationError) as ctx:
                    User.objects.create_user(
                        email=f'{role}@elegance.com.br',
                        password='StrongPassword123!',
                        full_name=f'Colaborador {role}',
                        role=role,
                        salon=None,
                    )
                self.assertIn('salon', ctx.exception.message_dict)

    def test_create_salon_member_and_normalize_email(self):
        user = User.objects.create_user(
            email='Gestora@Elegance.com.br',
            password='StrongPassword123!',
            full_name='Mariana Gestora',
            role=UserRoleChoices.GESTOR,
            salon=self.salon,
        )
        self.assertEqual(user.email, 'gestora@elegance.com.br')
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
        User.objects.create_user(
            email='recepcao@elegance.com.br',
            password='StrongPassword123!',
            full_name='Clara Recepção',
            role=UserRoleChoices.RECEPCIONISTA,
            salon=self.salon,
        )
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
