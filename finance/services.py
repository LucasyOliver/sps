from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from accounts.models import UserRoleChoices
from catalog.services import calculate_commission_amount, resolve_commission_percentage
from finance.models import (
    CashRegisterSession,
    CashRegisterStatusChoices,
    CashTransaction,
    CashTransactionTypeChoices,
    CommissionEntry,
    CommissionStatusChoices,
    OrderPayment,
    PaymentMethodChoices,
)
from fiscal.services import StubFiscalGatewayAdapter
from inventory.models import StockMovementTypeChoices
from inventory.services import StockService
from orders.models import ServiceOrder, ServiceOrderStatusChoices
from orders.services import OrderService

TWO_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')


def to_money(value) -> Decimal:
    if value in (None, ''):
        return ZERO
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class CashRegisterService:
    """Serviço de operação do Caixa Diário do salão (S07-T01, RF-009)."""

    @staticmethod
    def get_open_session(salon) -> CashRegisterSession | None:
        if salon is None:
            return None
        return (
            CashRegisterSession.objects.for_salon(salon)
            .filter(status=CashRegisterStatusChoices.OPEN)
            .first()
        )

    @classmethod
    def open_session(
        cls,
        *,
        salon,
        opened_by,
        opening_balance=ZERO,
        notes: str = '',
    ) -> CashRegisterSession:
        if salon is None or opened_by is None or opened_by.salon_id != salon.id:
            raise ValidationError('Operador inválido para abertura de caixa neste salão.')
        balance = to_money(opening_balance)
        if balance < ZERO:
            raise ValidationError({'opening_balance': 'O saldo inicial não pode ser negativo.'})

        with transaction.atomic():
            existing = (
                CashRegisterSession.objects.for_salon(salon)
                .select_for_update()
                .filter(status=CashRegisterStatusChoices.OPEN)
                .first()
            )
            if existing is not None:
                raise ValidationError('Já existe uma sessão de caixa aberta neste salão.')

            session = CashRegisterSession(
                salon=salon,
                opened_by=opened_by,
                opened_at=timezone.now(),
                opening_balance=balance,
                closing_balance_expected=balance,
                status=CashRegisterStatusChoices.OPEN,
                notes=(notes or '').strip(),
            )
            session.full_clean()
            session.save()
            return session

    @classmethod
    def record_manual_transaction(
        cls,
        *,
        salon,
        transaction_type: str,
        amount,
        description: str,
        payment_method: str = PaymentMethodChoices.CASH,
        actor=None,
    ) -> CashTransaction:
        if transaction_type not in (
            CashTransactionTypeChoices.MANUAL_INCOME,
            CashTransactionTypeChoices.MANUAL_EXPENSE,
        ):
            raise ValidationError(
                {'transaction_type': 'Lançamento manual deve ser Entrada avulsa ou Saída/Despesa.'}
            )
        money_amount = to_money(amount)
        if money_amount <= ZERO:
            raise ValidationError({'amount': 'O valor do lançamento deve ser maior que zero.'})
        desc_clean = (description or '').strip()
        if not desc_clean:
            raise ValidationError({'description': 'Informe a descrição do lançamento de caixa.'})

        with transaction.atomic():
            session = (
                CashRegisterSession.objects.for_salon(salon)
                .select_for_update()
                .filter(status=CashRegisterStatusChoices.OPEN)
                .first()
            )
            if session is None:
                raise ValidationError('Não há caixa aberto neste salão para registrar lançamentos.')

            tx = CashTransaction(
                salon=salon,
                cash_session=session,
                transaction_type=transaction_type,
                payment_method=payment_method,
                amount=money_amount,
                description=desc_clean,
                created_by=actor,
            )
            tx.full_clean()
            tx.save()

            session.closing_balance_expected = session.calculate_expected_balance()
            session.save(update_fields=['closing_balance_expected', 'updated_at'])
            return tx

    @classmethod
    def close_session(
        cls,
        *,
        salon,
        closed_by,
        closing_balance_counted,
        notes: str = '',
    ) -> CashRegisterSession:
        if salon is None or closed_by is None or closed_by.salon_id != salon.id:
            raise ValidationError('Operador inválido para fechamento de caixa neste salão.')
        counted = to_money(closing_balance_counted)
        if counted < ZERO:
            raise ValidationError(
                {'closing_balance_counted': 'O saldo conferido não pode ser negativo.'}
            )

        with transaction.atomic():
            session = (
                CashRegisterSession.objects.for_salon(salon)
                .select_for_update()
                .filter(status=CashRegisterStatusChoices.OPEN)
                .first()
            )
            if session is None:
                raise ValidationError('Não há sessão de caixa aberta neste salão para fechar.')

            session.closing_balance_expected = session.calculate_expected_balance()
            session.closing_balance_counted = counted
            session.closed_by = closed_by
            session.closed_at = timezone.now()
            session.status = CashRegisterStatusChoices.CLOSED
            if notes and notes.strip():
                session.notes = (
                    f'{session.notes}\n{notes.strip()}'.strip()
                    if session.notes
                    else notes.strip()
                )
            session.full_clean()
            session.save()
            return session


class OrderCheckoutService:
    """
    Serviço transacional de fechamento, pagamento e estorno de comandas
    (S07-T03, S07-T04, RF-007 a RF-009, RF-013, RNF-002).
    """

    @staticmethod
    def _normalize_payments(payments) -> list[dict]:
        if not payments:
            raise ValidationError('Informe pelo menos um meio de pagamento para fechar a comanda.')
        normalized = []
        valid_methods = set(PaymentMethodChoices.values)
        for idx, entry in enumerate(payments, start=1):
            method = (entry.get('payment_method') or '').strip()
            amount = to_money(entry.get('amount'))
            if method not in valid_methods:
                raise ValidationError(f'Meio de pagamento inválido na parcela #{idx}.')
            if amount <= ZERO:
                raise ValidationError(f'O valor da parcela #{idx} deve ser maior que zero.')
            normalized.append({'payment_method': method, 'amount': amount})
        return normalized

    @classmethod
    def close_and_pay_order(
        cls,
        *,
        salon,
        order: ServiceOrder,
        payments: list[dict],
        actor,
        fiscal_adapter=None,
    ) -> ServiceOrder:
        if salon is None or order is None or order.salon_id != salon.id:
            raise ValidationError('Comanda inválida ou pertencente a outro salão.')
        if actor is None or actor.salon_id != salon.id:
            raise ValidationError('Operador inválido para este salão.')

        normalized_payments = cls._normalize_payments(payments)
        adapter = fiscal_adapter or StubFiscalGatewayAdapter()

        with transaction.atomic():
            # 1. Bloqueia a comanda e garante status 'aberta'
            locked_order = ServiceOrder.objects.select_for_update().get(
                pk=order.pk,
                salon=salon,
            )
            if locked_order.status != ServiceOrderStatusChoices.OPEN:
                raise ValidationError(
                    f'A comanda #{locked_order.pk} não está aberta (status atual: '
                    f'{locked_order.get_status_display()}).'
                )

            OrderService.recalculate_totals(locked_order)
            service_items = list(
                locked_order.service_items.select_related('service', 'professional')
            )
            product_items = list(
                locked_order.product_items.select_related('product')
            )
            if not service_items and not product_items:
                raise ValidationError(
                    'Não é possível fechar e pagar uma comanda sem nenhum serviço ou produto.'
                )

            # 2. Verifica que o caixa diário do salão está aberto
            cash_session = (
                CashRegisterSession.objects.for_salon(salon)
                .select_for_update()
                .filter(status=CashRegisterStatusChoices.OPEN)
                .first()
            )
            if cash_session is None:
                raise ValidationError(
                    'Não há caixa diário aberto neste salão. Abra o caixa antes de fechar a comanda.'
                )

            # 3. Verifica equivalência exata entre a soma dos pagamentos e total_amount
            paid_sum = sum((p['amount'] for p in normalized_payments), ZERO)
            if paid_sum != locked_order.total_amount:
                raise ValidationError(
                    f'A soma dos pagamentos (R$ {paid_sum}) difere do total líquido da comanda '
                    f'(R$ {locked_order.total_amount}).'
                )

            # 4. Baixa atômica de estoque para cada produto vendido (aborta tudo se faltar saldo)
            for prod_item in product_items:
                StockService.register_movement(
                    salon=salon,
                    product=prod_item.product,
                    movement_type=StockMovementTypeChoices.SALE_OUT,
                    quantity=prod_item.quantity,
                    actor=actor,
                    order=locked_order,
                    reason=f'Venda em Comanda #{locked_order.pk}',
                )

            # 5. Gera comissões exclusivamente no pagamento (RF-009)
            for srv_item in service_items:
                pct = resolve_commission_percentage(
                    salon,
                    srv_item.professional,
                    srv_item.service,
                )
                comm_amount = calculate_commission_amount(srv_item.net_price, pct)
                srv_item.applied_commission_pct = pct
                srv_item.save(update_fields=['applied_commission_pct', 'updated_at'])

                comm_entry = CommissionEntry(
                    salon=salon,
                    order=locked_order,
                    order_service_item=srv_item,
                    professional=srv_item.professional,
                    base_amount=srv_item.net_price,
                    commission_pct=pct,
                    commission_amount=comm_amount,
                    status=CommissionStatusChoices.PENDING,
                )
                comm_entry.full_clean()
                comm_entry.save()

            # 6. Registra pagamentos, lançamentos no caixa, fecha comanda e gera registro fiscal
            for p_data in normalized_payments:
                payment = OrderPayment(
                    salon=salon,
                    order=locked_order,
                    cash_session=cash_session,
                    payment_method=p_data['payment_method'],
                    amount=p_data['amount'],
                )
                payment.full_clean()
                payment.save()

                tx = CashTransaction(
                    salon=salon,
                    cash_session=cash_session,
                    transaction_type=CashTransactionTypeChoices.ORDER_RECEIPT,
                    payment_method=p_data['payment_method'],
                    amount=p_data['amount'],
                    order=locked_order,
                    description=f'Recebimento da Comanda #{locked_order.pk}',
                    created_by=actor,
                )
                tx.full_clean()
                tx.save()

            cash_session.closing_balance_expected = cash_session.calculate_expected_balance()
            cash_session.save(update_fields=['closing_balance_expected', 'updated_at'])

            now = timezone.now()
            locked_order.status = ServiceOrderStatusChoices.CLOSED_PAID
            locked_order.closed_at = now
            locked_order.closed_by = actor
            locked_order.save(
                update_fields=['status', 'closed_at', 'closed_by', 'updated_at']
            )

            adapter.prepare_from_order(locked_order)
            return locked_order

    @classmethod
    def reverse_paid_order(
        cls,
        *,
        salon,
        order: ServiceOrder,
        actor,
        reason: str,
        fiscal_adapter=None,
    ) -> ServiceOrder:
        if salon is None or order is None or order.salon_id != salon.id:
            raise ValidationError('Comanda inválida ou pertencente a outro salão.')
        if (
            actor is None
            or actor.salon_id != salon.id
            or actor.role != UserRoleChoices.GESTOR
        ):
            raise PermissionDenied(
                'Apenas o Gestor do salão possui permissão para estornar uma comanda paga.'
            )

        reason_clean = (reason or '').strip()
        if not reason_clean:
            raise ValidationError(
                {'reason': 'Informe o motivo do estorno da comanda paga para auditoria.'}
            )

        adapter = fiscal_adapter or StubFiscalGatewayAdapter()

        with transaction.atomic():
            locked_order = ServiceOrder.objects.select_for_update().get(
                pk=order.pk,
                salon=salon,
            )
            if locked_order.status != ServiceOrderStatusChoices.CLOSED_PAID:
                raise ValidationError(
                    'Apenas comandas com status "Fechada / Paga" podem ser estornadas.'
                )

            cash_session = (
                CashRegisterSession.objects.for_salon(salon)
                .select_for_update()
                .filter(status=CashRegisterStatusChoices.OPEN)
                .first()
            )
            if cash_session is None:
                raise ValidationError(
                    'Abra uma sessão de caixa no salão antes de realizar o estorno financeiro.'
                )

            now = timezone.now()

            # 1. Estorna pagamentos e lança saída de estorno no caixa aberto
            for payment in locked_order.payments.filter(is_reversed=False):
                payment.is_reversed = True
                payment.reversed_at = now
                payment.save(update_fields=['is_reversed', 'reversed_at', 'updated_at'])

                tx = CashTransaction(
                    salon=salon,
                    cash_session=cash_session,
                    transaction_type=CashTransactionTypeChoices.ORDER_REVERSAL,
                    payment_method=payment.payment_method,
                    amount=payment.amount,
                    order=locked_order,
                    description=f'Estorno da Comanda #{locked_order.pk}: {reason_clean}',
                    created_by=actor,
                )
                tx.full_clean()
                tx.save()

            cash_session.closing_balance_expected = cash_session.calculate_expected_balance()
            cash_session.save(update_fields=['closing_balance_expected', 'updated_at'])

            # 2. Estorna comissões geradas pela comanda
            for comm in locked_order.commission_entries.exclude(
                status=CommissionStatusChoices.REVERSED
            ):
                comm.status = CommissionStatusChoices.REVERSED
                comm.reversed_at = now
                comm.save(update_fields=['status', 'reversed_at', 'updated_at'])

            # 3. Devolve produtos vendidos ao estoque com movimentação auditada 'estorno_comanda'
            for prod_item in locked_order.product_items.select_related('product'):
                StockService.register_movement(
                    salon=salon,
                    product=prod_item.product,
                    movement_type=StockMovementTypeChoices.ORDER_REVERSAL,
                    quantity=prod_item.quantity,
                    actor=actor,
                    order=locked_order,
                    reason=f'Estorno da Comanda #{locked_order.pk}: {reason_clean}',
                )

            # 4. Atualiza status da comanda e do registro fiscal preparatório
            locked_order.status = ServiceOrderStatusChoices.CANCELLED
            locked_order.cancelled_at = now
            locked_order.cancellation_reason = f'Estorno de comanda paga: {reason_clean}'
            locked_order.save(
                update_fields=[
                    'status',
                    'cancelled_at',
                    'cancellation_reason',
                    'updated_at',
                ]
            )

            adapter.cancel_from_order_reversal(locked_order, reason=reason_clean)
            return locked_order


class CommissionService:
    """Serviço de apuração e baixa de repasse de comissões aos profissionais (S07-T04, RF-009)."""

    @staticmethod
    def pay_commission_entries(*, salon, entry_ids: list[int], actor) -> int:
        if (
            salon is None
            or actor is None
            or actor.salon_id != salon.id
            or actor.role != UserRoleChoices.GESTOR
        ):
            raise PermissionDenied(
                'Apenas o Gestor do salão pode registrar o pagamento de repasse de comissões.'
            )
        if not entry_ids:
            raise ValidationError('Selecione ao menos uma comissão pendente para baixa.')

        now = timezone.now()
        with transaction.atomic():
            entries = list(
                CommissionEntry.objects.for_salon(salon)
                .select_for_update()
                .filter(
                    pk__in=entry_ids,
                    status=CommissionStatusChoices.PENDING,
                )
            )
            if not entries:
                raise ValidationError(
                    'Nenhuma comissão pendente válida encontrada para os itens selecionados.'
                )
            for entry in entries:
                entry.status = CommissionStatusChoices.PAID
                entry.paid_at = now
                entry.paid_by = actor
                entry.save(update_fields=['status', 'paid_at', 'paid_by', 'updated_at'])
            return len(entries)
