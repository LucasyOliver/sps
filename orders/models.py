from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from base.models import TenantScopedModel

ZERO = Decimal('0.00')
MONEY_VALIDATORS = [MinValueValidator(ZERO)]


class ServiceOrderStatusChoices(models.TextChoices):
    OPEN = 'aberta', 'Aberta'
    CLOSED_PAID = 'fechada_paga', 'Fechada / Paga'
    CANCELLED = 'cancelada', 'Cancelada'


class ServiceOrder(TenantScopedModel):
    appointment = models.ForeignKey(
        'scheduling.Appointment',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='service_orders',
        verbose_name='Agendamento de origem',
    )
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='service_orders',
        verbose_name='Cliente',
        help_text='Opcional apenas para venda avulsa de balcão sem identificação.',
    )
    status = models.CharField(
        'Status',
        max_length=20,
        choices=ServiceOrderStatusChoices.choices,
        default=ServiceOrderStatusChoices.OPEN,
    )
    subtotal_services = models.DecimalField(
        'Subtotal de serviços (R$)', max_digits=10, decimal_places=2, default=ZERO
    )
    subtotal_products = models.DecimalField(
        'Subtotal de produtos (R$)', max_digits=10, decimal_places=2, default=ZERO
    )
    discount_amount = models.DecimalField(
        'Desconto geral (R$)', max_digits=10, decimal_places=2, default=ZERO,
        validators=MONEY_VALIDATORS,
    )
    surcharge_amount = models.DecimalField(
        'Acréscimo (R$)', max_digits=10, decimal_places=2, default=ZERO,
        validators=MONEY_VALIDATORS,
    )
    total_amount = models.DecimalField(
        'Total líquido (R$)', max_digits=10, decimal_places=2, default=ZERO
    )
    notes = models.TextField('Observações', blank=True)
    opened_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opened_service_orders',
        verbose_name='Aberta por',
    )
    closed_at = models.DateTimeField('Fechada em', null=True, blank=True)
    closed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_service_orders',
        verbose_name='Fechada por',
    )
    cancelled_at = models.DateTimeField('Cancelada em', null=True, blank=True)
    cancellation_reason = models.CharField('Motivo do cancelamento', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Comanda'
        verbose_name_plural = 'Comandas'
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['appointment'],
                condition=~models.Q(status='cancelada'),
                name='unique_active_order_per_appointment',
            ),
        ]
        indexes = [
            models.Index(fields=['salon', 'status', 'created_at'], name='idx_order_salon_status'),
        ]

    def __str__(self):
        client_name = self.client.full_name if self.client_id else 'Venda avulsa'
        return f'Comanda #{self.pk} — {client_name} ({self.get_status_display()})'

    @property
    def is_open(self) -> bool:
        return self.status == ServiceOrderStatusChoices.OPEN

    def clean(self):
        super().clean()
        errors = {}
        if self.client_id and self.salon_id and self.client.salon_id != self.salon_id:
            errors['client'] = 'O cliente selecionado pertence a outro salão.'
        if self.appointment_id and self.salon_id and self.appointment.salon_id != self.salon_id:
            errors['appointment'] = 'O agendamento selecionado pertence a outro salão.'
        if errors:
            raise ValidationError(errors)


class OrderServiceItem(TenantScopedModel):
    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name='service_items',
        verbose_name='Comanda',
    )
    service = models.ForeignKey(
        'catalog.Service',
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='Serviço',
    )
    professional = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='order_service_items',
        verbose_name='Profissional executante',
    )
    gross_price = models.DecimalField(
        'Valor bruto (R$)', max_digits=10, decimal_places=2, validators=MONEY_VALIDATORS
    )
    discount_amount = models.DecimalField(
        'Desconto do item (R$)', max_digits=10, decimal_places=2, default=ZERO,
        validators=MONEY_VALIDATORS,
    )
    net_price = models.DecimalField('Valor líquido (R$)', max_digits=10, decimal_places=2)
    applied_commission_pct = models.DecimalField(
        'Comissão aplicada (%)',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(ZERO), MaxValueValidator(Decimal('100.00'))],
        help_text='Preenchido somente no fechamento/pagamento da comanda (RF-009).',
    )

    class Meta:
        verbose_name = 'Item de serviço da comanda'
        verbose_name_plural = 'Itens de serviço da comanda'
        ordering = ['id']

    def __str__(self):
        return f'{self.service.name} — {self.professional.full_name} (R$ {self.net_price})'

    def clean(self):
        super().clean()
        errors = {}
        if self.salon_id:
            if self.order_id and self.order.salon_id != self.salon_id:
                errors['order'] = 'A comanda pertence a outro salão.'
            if self.service_id and self.service.salon_id != self.salon_id:
                errors['service'] = 'O serviço selecionado pertence a outro salão.'
            if self.professional_id and self.professional.salon_id != self.salon_id:
                errors['professional'] = 'O profissional selecionado pertence a outro salão.'
        if (
            self.gross_price is not None
            and self.discount_amount is not None
            and self.discount_amount > self.gross_price
        ):
            errors['discount_amount'] = 'O desconto do item não pode ser maior que o valor bruto.'
        if errors:
            raise ValidationError(errors)


class OrderProductItem(TenantScopedModel):
    order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name='product_items',
        verbose_name='Comanda',
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='Produto',
    )
    quantity = models.PositiveIntegerField('Quantidade', validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        'Valor unitário (R$)', max_digits=10, decimal_places=2, validators=MONEY_VALIDATORS
    )
    total_price = models.DecimalField('Valor total (R$)', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Item de produto da comanda'
        verbose_name_plural = 'Itens de produto da comanda'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product'],
                name='unique_product_per_order',
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='order_product_item_quantity_positive',
            ),
        ]

    def __str__(self):
        return f'{self.quantity}x {self.product.name} (R$ {self.total_price})'

    def clean(self):
        super().clean()
        errors = {}
        if self.salon_id:
            if self.order_id and self.order.salon_id != self.salon_id:
                errors['order'] = 'A comanda pertence a outro salão.'
            if self.product_id and self.product.salon_id != self.salon_id:
                errors['product'] = 'O produto selecionado pertence a outro salão.'
        if self.quantity is not None and self.quantity <= 0:
            errors['quantity'] = 'A quantidade deve ser maior que zero.'
        if errors:
            raise ValidationError(errors)
