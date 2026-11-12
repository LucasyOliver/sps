import re
from django.core.exceptions import ValidationError
from django.db import models
from base.models import TimeStampedModel


class TaxRegimeChoices(models.TextChoices):
    NOT_CONFIGURED = 'nao_configurado', 'Não configurado'
    MEI = 'mei', 'MEI (Microempreendedor Individual)'
    SIMPLES_NACIONAL = 'simples_nacional', 'Simples Nacional'
    LUCRO_PRESUMIDO = 'lucro_presumido', 'Lucro Presumido'
    LUCRO_REAL = 'lucro_real', 'Lucro Real'


def normalize_digits(value):
    if not value:
        return ''
    return re.sub(r'\D', '', value)


class Salon(TimeStampedModel):
    name = models.CharField('Razão social / Nome empresarial', max_length=160)
    trade_name = models.CharField('Nome fantasia do salão', max_length=120)
    slug = models.SlugField(
        'Identificador público (slug)',
        max_length=80,
        unique=True,
        help_text='Usado na URL pública de agendamento (/s/<slug>/).',
    )
    phone = models.CharField('Telefone / WhatsApp', max_length=25, blank=True)
    email = models.EmailField('E-mail de contato', blank=True)
    timezone = models.CharField(
        'Fuso horário',
        max_length=50,
        default='America/Sao_Paulo',
    )
    cancellation_min_hours = models.PositiveSmallIntegerField(
        'Antecedência mínima para cancelamento público (horas)',
        default=2,
        help_text='Prazo mínimo em horas antes do início para o cliente cancelar pelo link público.',
    )
    is_active = models.BooleanField('Ativo', default=True)

    # Dados fiscais preparatórios para futura emissão de NFS-e / NFC-e (RF-001, DEC-003)
    cnpj = models.CharField(
        'CNPJ',
        max_length=18,
        blank=True,
        help_text='Apenas números ou formato padrão (14 dígitos).',
    )
    municipal_registration = models.CharField(
        'Inscrição Municipal (IM)',
        max_length=30,
        blank=True,
    )
    state_registration = models.CharField(
        'Inscrição Estadual (IE)',
        max_length=30,
        blank=True,
    )
    tax_regime = models.CharField(
        'Regime tributário',
        max_length=25,
        choices=TaxRegimeChoices.choices,
        default=TaxRegimeChoices.NOT_CONFIGURED,
    )
    is_partner_salon_regime = models.BooleanField(
        'Adota regime Salão-Parceiro (Lei 13.352/2016)',
        default=False,
    )
    ibge_city_code = models.CharField(
        'Código IBGE do município',
        max_length=7,
        blank=True,
    )
    address_street = models.CharField('Logradouro', max_length=150, blank=True)
    address_number = models.CharField('Número', max_length=20, blank=True)
    address_complement = models.CharField('Complemento', max_length=80, blank=True)
    address_neighborhood = models.CharField('Bairro', max_length=80, blank=True)
    address_city = models.CharField('Cidade', max_length=80, blank=True)
    address_state = models.CharField('UF', max_length=2, blank=True)
    address_zip_code = models.CharField('CEP', max_length=10, blank=True)

    class Meta:
        verbose_name = 'Salão'
        verbose_name_plural = 'Salões'
        ordering = ['trade_name']

    def __str__(self):
        return f'{self.trade_name} ({self.slug})'

    def clean(self):
        super().clean()
        if self.cnpj:
            digits = normalize_digits(self.cnpj)
            if len(digits) != 14:
                raise ValidationError(
                    {'cnpj': 'O CNPJ informado deve conter exatamente 14 dígitos numéricos.'}
                )
            self.cnpj = digits
        if self.ibge_city_code:
            ibge_digits = normalize_digits(self.ibge_city_code)
            if len(ibge_digits) != 7:
                raise ValidationError(
                    {'ibge_city_code': 'O código IBGE do município deve conter 7 dígitos.'}
                )
            self.ibge_city_code = ibge_digits
