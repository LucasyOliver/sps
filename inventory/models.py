from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from base.models import TenantScopedModel


class ProductUsageTypeChoices(models.TextChoices):
    SALE = 'venda', 'Venda ao cliente'
    INTERNAL = 'consumo_interno', 'Consumo interno'
    BOTH = 'ambos', 'Venda e consumo interno'


class ProductUnitChoices(models.TextChoices):
    UNIT = 'un', 'Unidade'
    KIT = 'kit', 'Kit'
    ML = 'ml', 'Mililitro'
    GRAM = 'g', 'Grama'


class TaxOriginChoices(models.TextChoices):
    NATIONAL = '0', '0 - Nacional'
    FOREIGN_DIRECT = '1', '1 - Estrangeira (importação direta)'
    FOREIGN_INTERNAL = '2', '2 - Estrangeira (adquirida no mercado interno)'


class StockMovementTypeChoices(models.TextChoices):
    PURCHASE_IN = 'entrada_compra', 'Entrada por compra'
    SALE_OUT = 'saida_venda_comanda', 'Saída por venda em comanda'
    INTERNAL_OUT = 'saida_consumo_interno', 'Saída por consumo interno'
    ADJUSTMENT = 'ajuste_inventario', 'Ajuste de inventário'
    ORDER_REVERSAL = 'estorno_comanda', 'Estorno de comanda'


SALE_USAGE_TYPES = (ProductUsageTypeChoices.SALE, ProductUsageTypeChoices.BOTH)
INTERNAL_USAGE_TYPES = (ProductUsageTypeChoices.INTERNAL, ProductUsageTypeChoices.BOTH)

PERCENT_VALIDATORS = [
    MinValueValidator(Decimal('0.00')),
    MaxValueValidator(Decimal('100.00')),
]


class Product(TenantScopedModel):
    name = models.CharField('Nome do produto', max_length=150)
    sku = models.CharField(
        'SKU / Código de barras',
        max_length=60,
        blank=True,
        help_text='Código interno ou EAN do produto (único por salão quando informado).',
    )
    usage_type = models.CharField(
        'Tipo de uso',
        max_length=20,
        choices=ProductUsageTypeChoices.choices,
        default=ProductUsageTypeChoices.SALE,
    )
    unit = models.CharField(
        'Unidade de medida',
        max_length=5,
        choices=ProductUnitChoices.choices,
        default=ProductUnitChoices.UNIT,
    )
    cost_price = models.DecimalField(
        'Preço de custo (R$)',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    sale_price = models.DecimalField(
        'Preço de venda (R$)',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    current_stock = models.PositiveIntegerField(
        'Saldo atual',
        default=0,
        editable=False,
        help_text='Alterado exclusivamente por movimentações de estoque auditadas.',
    )
    min_stock_alert = models.PositiveIntegerField('Estoque mínimo (alerta)', default=0)
    is_active = models.BooleanField('Ativo', default=True)

    # Metadados fiscais preparatórios para futura NFC-e / NF-e (RF-008, DEC-003)
    ncm_code = models.CharField('NCM', max_length=10, blank=True, help_text='8 dígitos (ex.: 33051000).')
    cest_code = models.CharField('CEST', max_length=9, blank=True, help_text='7 dígitos (ex.: 2002100).')
    cfop_default = models.CharField('CFOP padrão', max_length=4, blank=True, help_text='4 dígitos (ex.: 5102).')
    tax_origin = models.CharField(
        'Origem da mercadoria',
        max_length=1,
        choices=TaxOriginChoices.choices,
        default=TaxOriginChoices.NATIONAL,
    )
    icms_rate_pct = models.DecimalField(
        'Alíquota ICMS referencial (%)',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=PERCENT_VALIDATORS,
    )
    pis_cofins_regime = models.CharField(
        'Regime PIS/COFINS referencial',
        max_length=60,
        blank=True,
        help_text='Ex.: monofásico, alíquota zero, tributação normal.',
    )

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['salon', 'name'],
                name='unique_product_name_per_salon',
            ),
            models.UniqueConstraint(
                fields=['salon', 'sku'],
                condition=~models.Q(sku=''),
                name='unique_product_sku_per_salon',
            ),
        ]

    def __str__(self):
        return f'{self.name} (saldo: {self.current_stock} {self.unit})'

    @property
    def is_below_min_stock(self) -> bool:
        return self.current_stock <= self.min_stock_alert

    @property
    def is_sellable(self) -> bool:
        return self.usage_type in SALE_USAGE_TYPES

    def clean_fields(self, exclude=None):
        for field_name in ('ncm_code', 'cest_code', 'cfop_default'):
            raw_value = getattr(self, field_name, None)
            if raw_value:
                setattr(
                    self,
                    field_name,
                    raw_value.replace('.', '').replace('-', '').strip(),
                )
        if self.sku:
            self.sku = self.sku.strip()
        super().clean_fields(exclude=exclude)

    def clean(self):
        super().clean()
        errors = {}
        digit_rules = (
            ('ncm_code', 8, 'O NCM deve conter 8 dígitos numéricos.'),
            ('cest_code', 7, 'O CEST deve conter 7 dígitos numéricos.'),
            ('cfop_default', 4, 'O CFOP deve conter 4 dígitos numéricos.'),
        )
        for field_name, size, message in digit_rules:
            raw_value = (getattr(self, field_name) or '').replace('.', '').replace('-', '').strip()
            if raw_value and (len(raw_value) != size or not raw_value.isdigit()):
                errors[field_name] = message
            else:
                setattr(self, field_name, raw_value)
        if self.sku:
            self.sku = self.sku.strip()
        if errors:
            raise ValidationError(errors)


class StockMovement(TenantScopedModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name='Produto',
    )
    movement_type = models.CharField(
        'Tipo de movimentação',
        max_length=25,
        choices=StockMovementTypeChoices.choices,
    )
    quantity_delta = models.IntegerField(
        'Variação de quantidade',
        help_text='Positivo para entradas e negativo para saídas.',
    )
    balance_after = models.PositiveIntegerField('Saldo após a movimentação')
    order = models.ForeignKey(
        'orders.ServiceOrder',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Comanda vinculada',
    )
    actor = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Responsável',
    )
    reason = models.CharField('Motivo / Observação', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Movimentação de estoque'
        verbose_name_plural = 'Movimentações de estoque'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['salon', 'product', 'created_at'], name='idx_stock_mov_salon_product'),
        ]

    def __str__(self):
        signal = '+' if self.quantity_delta > 0 else ''
        return (
            f'{self.product.name}: {signal}{self.quantity_delta} '
            f'({self.get_movement_type_display()}) → saldo {self.balance_after}'
        )

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError('Movimentações de estoque são imutáveis após o registro.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Movimentações de estoque não podem ser excluídas (livro razão auditável).')
