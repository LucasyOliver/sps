from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from base.models import TenantScopedModel


class ServiceCategory(TenantScopedModel):
    name = models.CharField('Nome da categoria', max_length=120)
    description = models.CharField('Descrição', max_length=255, blank=True)
    is_active = models.BooleanField('Ativa', default=True)

    class Meta:
        verbose_name = 'Categoria de serviço'
        verbose_name_plural = 'Categorias de serviços'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['salon', 'name'],
                name='unique_service_category_per_salon',
            )
        ]

    def __str__(self):
        return f'{self.name} ({self.salon.trade_name})'


class Service(TenantScopedModel):
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services',
        verbose_name='Categoria',
    )
    name = models.CharField('Nome do serviço', max_length=150)
    description = models.TextField('Descrição', blank=True)
    duration_minutes = models.PositiveIntegerField(
        'Duração estimada (minutos)',
        default=30,
        validators=[MinValueValidator(1)],
        help_text='Duração em minutos (ex.: 15, 30, 45, 60).',
    )
    base_price = models.DecimalField(
        'Preço base (R$)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    default_commission_pct = models.DecimalField(
        'Comissão padrão (%)',
        max_digits=5,
        decimal_places=2,
        default=Decimal('40.00'),
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00')),
        ],
    )
    professionals = models.ManyToManyField(
        'accounts.User',
        blank=True,
        related_name='enabled_services',
        verbose_name='Profissionais habilitados',
    )
    is_active = models.BooleanField('Ativo', default=True)

    # Metadados fiscais preparatórios para futura emissão de NFS-e / Salão-Parceiro (RF-003, DEC-003)
    lc116_service_code = models.CharField(
        'Código de serviço municipal (LC 116)',
        max_length=20,
        blank=True,
        help_text='Ex.: 06.01 (Barbearia, cabeleireiros, manicuros, pedicuros e congêneres).',
    )
    cnae_code = models.CharField(
        'Código CNAE',
        max_length=20,
        blank=True,
        help_text='Ex.: 9602-5/01.',
    )
    iss_rate_pct = models.DecimalField(
        'Alíquota ISS referencial (%)',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00')),
        ],
    )

    class Meta:
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['salon', 'name'],
                name='unique_service_name_per_salon',
            )
        ]

    def __str__(self):
        return f'{self.name} — R$ {self.base_price} ({self.duration_minutes} min)'

    def clean(self):
        super().clean()
        errors = {}
        if self.category_id and self.salon_id:
            if self.category.salon_id != self.salon_id:
                errors['category'] = 'A categoria selecionada pertence a outro salão.'

        if self.duration_minutes is not None and self.duration_minutes <= 0:
            errors['duration_minutes'] = 'A duração do serviço deve ser maior que zero.'

        if self.base_price is not None and self.base_price < Decimal('0.00'):
            errors['base_price'] = 'O preço base não pode ser negativo.'

        if self.default_commission_pct is not None and (
            self.default_commission_pct < Decimal('0.00')
            or self.default_commission_pct > Decimal('100.00')
        ):
            errors['default_commission_pct'] = (
                'O percentual de comissão padrão deve estar entre 0% e 100%.'
            )

        if self.iss_rate_pct is not None and (
            self.iss_rate_pct < Decimal('0.00') or self.iss_rate_pct > Decimal('100.00')
        ):
            errors['iss_rate_pct'] = 'A alíquota de ISS deve estar entre 0% e 100%.'

        if errors:
            raise ValidationError(errors)


class ProfessionalServiceCommission(TenantScopedModel):
    professional = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='service_commissions',
        verbose_name='Profissional',
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='professional_commissions',
        verbose_name='Serviço',
    )
    commission_pct = models.DecimalField(
        'Comissão específica (%)',
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00')),
        ],
    )
    is_active = models.BooleanField('Regra ativa', default=True)

    class Meta:
        verbose_name = 'Regra de comissão por profissional e serviço'
        verbose_name_plural = 'Regras de comissão por profissional e serviço'
        ordering = ['service__name', 'professional__full_name']
        constraints = [
            models.UniqueConstraint(
                fields=['salon', 'professional', 'service'],
                name='unique_professional_service_commission',
            )
        ]

    def __str__(self):
        return (
            f'{self.professional.full_name} — {self.service.name}: '
            f'{self.commission_pct}%'
        )

    def clean(self):
        super().clean()
        errors = {}
        if self.professional_id and self.salon_id:
            if self.professional.salon_id != self.salon_id:
                errors['professional'] = 'O profissional selecionado não pertence a este salão.'

        if self.service_id and self.salon_id:
            if self.service.salon_id != self.salon_id:
                errors['service'] = 'O serviço selecionado não pertence a este salão.'

        if self.commission_pct is not None and (
            self.commission_pct < Decimal('0.00')
            or self.commission_pct > Decimal('100.00')
        ):
            errors['commission_pct'] = (
                'O percentual de comissão específica deve estar entre 0% e 100%.'
            )

        if errors:
            raise ValidationError(errors)
