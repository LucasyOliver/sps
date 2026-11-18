from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from base.models import TenantScopedModel

ZERO = Decimal('0.00')
ONE_CENT = Decimal('0.01')
MONEY_VALIDATORS = [MinValueValidator(ZERO)]
POSITIVE_MONEY_VALIDATORS = [MinValueValidator(ONE_CENT)]


class CashRegisterStatusChoices(models.TextChoices):
    OPEN = 'aberto', 'Aberto'
    CLOSED = 'fechado', 'Fechado'


class PaymentMethodChoices(models.TextChoices):
    CASH = 'dinheiro', 'Dinheiro'
    PIX = 'pix', 'Pix'
    CREDIT_CARD = 'cartao_credito', 'Cartão de Crédito'
    DEBIT_CARD = 'cartao_debito', 'Cartão de Débito'


class CashTransactionTypeChoices(models.TextChoices):
    ORDER_RECEIPT = 'recebimento_comanda', 'Recebimento de comanda'
    MANUAL_INCOME = 'entrada_avulsa', 'Entrada avulsa / Suprimento'
    MANUAL_EXPENSE = 'saida_despesa', 'Saída / Despesa do salão'
    ORDER_REVERSAL = 'estorno_comanda', 'Estorno de comanda'


INFLOW_TRANSACTION_TYPES = (
    CashTransactionTypeChoices.ORDER_RECEIPT,
    CashTransactionTypeChoices.MANUAL_INCOME,
)
OUTFLOW_TRANSACTION_TYPES = (
    CashTransactionTypeChoices.MANUAL_EXPENSE,
    CashTransactionTypeChoices.ORDER_REVERSAL,
)


class CommissionStatusChoices(models.TextChoices):
    PENDING = 'pendente_repasse', 'Pendente de repasse'
    PAID = 'pago_ao_profissional', 'Pago ao profissional'
    REVERSED = 'estornado', 'Estornado'


class CashRegisterSession(TenantScopedModel):
    opened_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='opened_cash_sessions',
        verbose_name='Aberto por',
    )
    opened_at = models.DateTimeField('Aberto em', default=timezone.now)
    opening_balance = models.DecimalField(
        'Saldo inicial (R$)',
        max_digits=10,
        decimal_places=2,
        default=ZERO,
        validators=MONEY_VALIDATORS,
    )
    closed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='closed_cash_sessions',
        verbose_name='Fechado por',
    )
    closed_at = models.DateTimeField('Fechado em', null=True, blank=True)
    closing_balance_expected = models.DecimalField(
        'Saldo final esperado (R$)',
        max_digits=10,
        decimal_places=2,
        default=ZERO,
    )
    closing_balance_counted = models.DecimalField(
        'Saldo final conferido (R$)',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=MONEY_VALIDATORS,
    )
    status = models.CharField(
        'Status',
        max_length=15,
        choices=CashRegisterStatusChoices.choices,
        default=CashRegisterStatusChoices.OPEN,
    )
    notes = models.TextField('Observações', blank=True)

    class Meta:
        verbose_name = 'Sessão de caixa'
        verbose_name_plural = 'Sessões de caixa'
        ordering = ['-opened_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['salon'],
                condition=models.Q(status='aberto'),
                name='unique_open_cash_session_per_salon',
            ),
        ]

    def __str__(self):
        return (
            f'Caixa #{self.pk} ({self.salon.trade_name}) — '
            f'{self.opened_at:%d/%m/%Y %H:%M} ({self.get_status_display()})'
        )

    @property
    def is_open(self) -> bool:
        return self.status == CashRegisterStatusChoices.OPEN

    def calculate_expected_balance(self) -> Decimal:
        total = self.opening_balance or ZERO
        for tx in self.transactions.all():
            total += tx.signed_amount
        return total

    def clean(self):
        super().clean()
        errors = {}
        if self.salon_id and self.opened_by_id and self.opened_by.salon_id != self.salon_id:
            errors['opened_by'] = 'O operador de abertura pertence a outro salão.'
        if self.salon_id and self.closed_by_id and self.closed_by.salon_id != self.salon_id:
            errors['closed_by'] = 'O operador de fechamento pertence a outro salão.'
        if errors:
            raise ValidationError(errors)


class CashTransaction(TenantScopedModel):
    cash_session = models.ForeignKey(
        CashRegisterSession,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name='Sessão de caixa',
    )
    transaction_type = models.CharField(
        'Tipo de lançamento',
        max_length=25,
        choices=CashTransactionTypeChoices.choices,
    )
    payment_method = models.CharField(
        'Meio de pagamento',
        max_length=20,
        choices=PaymentMethodChoices.choices,
        default=PaymentMethodChoices.CASH,
    )
    amount = models.DecimalField(
        'Valor (R$)',
        max_digits=10,
        decimal_places=2,
        validators=POSITIVE_MONEY_VALIDATORS,
    )
    order = models.ForeignKey(
        'orders.ServiceOrder',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cash_transactions',
        verbose_name='Comanda vinculada',
    )
    description = models.CharField('Descrição', max_length=200)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_cash_transactions',
        verbose_name='Registrado por',
    )

    class Meta:
        verbose_name = 'Lançamento de caixa'
        verbose_name_plural = 'Lançamentos de caixa'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(
                fields=['salon', 'cash_session', 'created_at'],
                name='idx_cash_tx_salon_session',
            ),
        ]

    def __str__(self):
        sign = '+' if self.transaction_type in INFLOW_TRANSACTION_TYPES else '-'
        return f'{sign} R$ {self.amount} ({self.get_transaction_type_display()})'

    @property
    def signed_amount(self) -> Decimal:
        if self.transaction_type in OUTFLOW_TRANSACTION_TYPES:
            return -(self.amount or ZERO)
        return self.amount or ZERO

    def clean(self):
        super().clean()
        errors = {}
        if self.salon_id:
            if self.cash_session_id and self.cash_session.salon_id != self.salon_id:
                errors['cash_session'] = 'A sessão de caixa pertence a outro salão.'
            if self.order_id and self.order.salon_id != self.salon_id:
                errors['order'] = 'A comanda vinculada pertence a outro salão.'
        if errors:
            raise ValidationError(errors)


class OrderPayment(TenantScopedModel):
    order = models.ForeignKey(
        'orders.ServiceOrder',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name='Comanda',
    )
    cash_session = models.ForeignKey(
        CashRegisterSession,
        on_delete=models.PROTECT,
        related_name='order_payments',
        verbose_name='Sessão de caixa',
    )
    payment_method = models.CharField(
        'Meio de pagamento',
        max_length=20,
        choices=PaymentMethodChoices.choices,
    )
    amount = models.DecimalField(
        'Valor pago (R$)',
        max_digits=10,
        decimal_places=2,
        validators=POSITIVE_MONEY_VALIDATORS,
    )
    is_reversed = models.BooleanField('Estornado', default=False)
    reversed_at = models.DateTimeField('Estornado em', null=True, blank=True)

    class Meta:
        verbose_name = 'Pagamento de comanda'
        verbose_name_plural = 'Pagamentos de comandas'
        ordering = ['id']

    def __str__(self):
        return f'Comanda #{self.order_id} — {self.get_payment_method_display()}: R$ {self.amount}'

    def clean(self):
        super().clean()
        errors = {}
        if self.salon_id:
            if self.order_id and self.order.salon_id != self.salon_id:
                errors['order'] = 'A comanda pertence a outro salão.'
            if self.cash_session_id and self.cash_session.salon_id != self.salon_id:
                errors['cash_session'] = 'A sessão de caixa pertence a outro salão.'
        if errors:
            raise ValidationError(errors)


class CommissionEntry(TenantScopedModel):
    order = models.ForeignKey(
        'orders.ServiceOrder',
        on_delete=models.PROTECT,
        related_name='commission_entries',
        verbose_name='Comanda',
    )
    order_service_item = models.OneToOneField(
        'orders.OrderServiceItem',
        on_delete=models.PROTECT,
        related_name='commission_entry',
        verbose_name='Item de serviço da comanda',
    )
    professional = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='commission_entries',
        verbose_name='Profissional',
    )
    base_amount = models.DecimalField(
        'Valor base do serviço (R$)',
        max_digits=10,
        decimal_places=2,
        validators=MONEY_VALIDATORS,
    )
    commission_pct = models.DecimalField(
        'Percentual aplicado (%)',
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(ZERO), MaxValueValidator(Decimal('100.00'))],
    )
    commission_amount = models.DecimalField(
        'Valor da comissão (R$)',
        max_digits=10,
        decimal_places=2,
        validators=MONEY_VALIDATORS,
    )
    status = models.CharField(
        'Status',
        max_length=25,
        choices=CommissionStatusChoices.choices,
        default=CommissionStatusChoices.PENDING,
    )
    paid_at = models.DateTimeField('Pago ao profissional em', null=True, blank=True)
    paid_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paid_commission_entries',
        verbose_name='Baixado por',
    )
    reversed_at = models.DateTimeField('Estornado em', null=True, blank=True)

    class Meta:
        verbose_name = 'Lançamento de comissão'
        verbose_name_plural = 'Lançamentos de comissões'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(
                fields=['salon', 'professional', 'status'],
                name='idx_comm_salon_prof_status',
            ),
        ]

    def __str__(self):
        return (
            f'{self.professional.full_name} — Comanda #{self.order_id}: '
            f'R$ {self.commission_amount} ({self.commission_pct}%)'
        )

    def clean(self):
        super().clean()
        errors = {}
        if self.salon_id:
            if self.order_id and self.order.salon_id != self.salon_id:
                errors['order'] = 'A comanda pertence a outro salão.'
            if (
                self.order_service_item_id
                and self.order_service_item.salon_id != self.salon_id
            ):
                errors['order_service_item'] = 'O item de serviço pertence a outro salão.'
            if self.professional_id and self.professional.salon_id != self.salon_id:
                errors['professional'] = 'O profissional pertence a outro salão.'
        if errors:
            raise ValidationError(errors)
