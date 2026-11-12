from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from base.models import TimeStampedModel


class UserRoleChoices(models.TextChoices):
    SUPERADMIN_SAAS = 'superadmin_saas', 'Superadmin da Plataforma SaaS'
    GESTOR = 'gestor', 'Proprietário / Gestor do Salão'
    RECEPCIONISTA = 'recepcionista', 'Recepcionista / Atendente'
    PROFISSIONAL = 'profissional', 'Profissional / Especialista'


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('O endereço de e-mail é obrigatório para criar um usuário.')
        normalized_email = self.normalize_email(email).lower()
        user = self.model(email=normalized_email, **extra_fields)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRoleChoices.SUPERADMIN_SAAS)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser precisa ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser precisa ter is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    email = models.EmailField('E-mail', unique=True)
    full_name = models.CharField('Nome completo', max_length=150)
    phone = models.CharField('Telefone / WhatsApp', max_length=25, blank=True)
    role = models.CharField(
        'Perfil de acesso',
        max_length=25,
        choices=UserRoleChoices.choices,
        default=UserRoleChoices.PROFISSIONAL,
    )
    salon = models.ForeignKey(
        'salons.Salon',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Salão vinculado',
        help_text='Obrigatório para perfis internos do salão (Gestor, Recepcionista, Profissional).',
    )
    tax_document = models.CharField(
        'CPF / CNPJ (profissional parceiro)',
        max_length=18,
        blank=True,
        help_text='Documento opcional para preparação de rateio fiscal (Salão-Parceiro).',
    )
    is_active = models.BooleanField('Ativo', default=True)
    is_staff = models.BooleanField('Acesso ao Django Admin', default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['full_name', 'email']

    def __str__(self):
        return f'{self.full_name} <{self.email}>'

    @property
    def is_salon_member(self):
        return self.role in {
            UserRoleChoices.GESTOR,
            UserRoleChoices.RECEPCIONISTA,
            UserRoleChoices.PROFISSIONAL,
        }

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email).lower()

        if self.is_salon_member and self.salon_id is None:
            raise ValidationError(
                {
                    'salon': (
                        'Usuários com perfil interno de salão (Gestor, Recepcionista ou '
                        'Profissional) devem pertencer obrigatoriamente a um único salão fixo.'
                    )
                }
            )
