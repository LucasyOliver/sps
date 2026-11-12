import re
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from base.models import TenantScopedModel


def normalize_digits(value: str) -> str:
    if not value:
        return ''
    return re.sub(r'\D', '', value)


class Client(TenantScopedModel):
    full_name = models.CharField('Nome completo', max_length=160)
    phone = models.CharField(
        'Telefone / WhatsApp',
        max_length=20,
        help_text='Informe DDD + número (10 ou 11 dígitos).',
    )
    email = models.EmailField('E-mail', blank=True)
    birth_date = models.DateField('Data de nascimento', null=True, blank=True)
    notes = models.TextField(
        'Observações técnicas / Alergias / Preferências',
        blank=True,
    )
    is_active = models.BooleanField('Ativo', default=True)

    # Dados fiscais opcionais de tomador para futura emissão de NFS-e / NFC-e (RF-004, DEC-003)
    cpf_cnpj = models.CharField(
        'CPF ou CNPJ',
        max_length=18,
        blank=True,
        help_text='Apenas números ou formato padrão (11 dígitos para CPF ou 14 para CNPJ).',
    )
    address_street = models.CharField('Logradouro', max_length=160, blank=True)
    address_number = models.CharField('Número', max_length=20, blank=True)
    address_complement = models.CharField('Complemento', max_length=80, blank=True)
    address_neighborhood = models.CharField('Bairro', max_length=100, blank=True)
    address_city = models.CharField('Município', max_length=100, blank=True)
    address_state = models.CharField('UF', max_length=2, blank=True)
    address_zip_code = models.CharField('CEP', max_length=10, blank=True)
    ibge_city_code = models.CharField(
        'Código IBGE do município',
        max_length=7,
        blank=True,
        help_text='Código oficial de 7 dígitos do município (ex.: 3550308).',
    )

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['full_name']
        constraints = [
            models.UniqueConstraint(
                fields=['salon', 'phone'],
                name='unique_client_phone_per_salon',
            ),
            models.UniqueConstraint(
                fields=['salon', 'cpf_cnpj'],
                condition=~Q(cpf_cnpj=''),
                name='unique_client_cpf_cnpj_per_salon',
            ),
        ]

    def __str__(self):
        return f'{self.full_name} ({self.phone})'

    def clean(self):
        super().clean()
        errors = {}

        if self.phone:
            digits = normalize_digits(self.phone)
            if len(digits) not in (10, 11):
                errors['phone'] = (
                    'O telefone deve conter 10 ou 11 dígitos numéricos (com DDD).'
                )
            else:
                self.phone = digits
                if self.salon_id:
                    qs = Client.objects.for_salon(self.salon_id).filter(phone=self.phone)
                    if self.pk:
                        qs = qs.exclude(pk=self.pk)
                    if qs.exists():
                        errors['phone'] = (
                            'Já existe um cliente cadastrado com este telefone neste salão.'
                        )

        if self.cpf_cnpj:
            doc_digits = normalize_digits(self.cpf_cnpj)
            if len(doc_digits) not in (11, 14):
                errors['cpf_cnpj'] = (
                    'Informe um CPF válido (11 dígitos) ou CNPJ válido (14 dígitos).'
                )
            else:
                self.cpf_cnpj = doc_digits
                if self.salon_id:
                    qs = Client.objects.for_salon(self.salon_id).filter(
                        cpf_cnpj=self.cpf_cnpj
                    )
                    if self.pk:
                        qs = qs.exclude(pk=self.pk)
                    if qs.exists():
                        errors['cpf_cnpj'] = (
                            'Já existe um cliente cadastrado com este CPF/CNPJ neste salão.'
                        )

        if self.address_zip_code:
            zip_digits = normalize_digits(self.address_zip_code)
            if len(zip_digits) != 8:
                errors['address_zip_code'] = 'O CEP deve conter 8 dígitos numéricos.'
            else:
                self.address_zip_code = zip_digits

        if self.ibge_city_code:
            ibge_digits = normalize_digits(self.ibge_city_code)
            if len(ibge_digits) != 7:
                errors['ibge_city_code'] = (
                    'O código IBGE do município deve conter 7 dígitos numéricos.'
                )
            else:
                self.ibge_city_code = ibge_digits

        if self.address_state:
            self.address_state = self.address_state.strip().upper()
            if len(self.address_state) != 2 or not self.address_state.isalpha():
                errors['address_state'] = 'A UF deve conter 2 letras (ex.: SP, RJ).'

        if errors:
            raise ValidationError(errors)

    def get_appointment_history(self):
        """Retorna agendamentos do cliente quando o modelo Appointment estiver ativo."""
        if hasattr(self, 'appointments'):
            return self.appointments.all().order_by('-start_at')
        return []

    def get_service_order_history(self):
        """Retorna comandas do cliente quando o modelo ServiceOrder estiver ativo."""
        if hasattr(self, 'service_orders'):
            return self.service_orders.all().order_by('-created_at')
        return []
