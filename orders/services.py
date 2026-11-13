from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from accounts.models import UserRoleChoices
from inventory.models import Product
from orders.models import (
    OrderProductItem,
    OrderServiceItem,
    ServiceOrder,
    ServiceOrderStatusChoices,
)
from scheduling.models import AppointmentStatusChoices

TWO_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')

APPOINTMENT_STATUSES_ALLOWED_FOR_ORDER = (
    AppointmentStatusChoices.IN_PROGRESS,
    AppointmentStatusChoices.COMPLETED,
)


def to_money(value) -> Decimal:
    if value in (None, ''):
        return ZERO
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class OrderService:
    """
    Serviço de domínio das comandas de atendimento abertas (S06-T03, S06-T04, RF-007).
    O fechamento/pagamento, a baixa definitiva de estoque, as comissões e o registro fiscal
    pertencem à Sprint 07 (OrderCheckoutService). Aqui apenas comandas 'aberta' são editáveis.
    """

    # ---------------------------------------------------------------- utilidades
    @staticmethod
    def _lock_open_order(order: ServiceOrder) -> ServiceOrder:
        locked = ServiceOrder.objects.select_for_update().get(pk=order.pk, salon_id=order.salon_id)
        if locked.status != ServiceOrderStatusChoices.OPEN:
            raise ValidationError(
                f'A comanda #{locked.pk} está "{locked.get_status_display()}" e não pode ser alterada.'
            )
        return locked

    @staticmethod
    def _validate_professional_for_service(salon, professional, service):
        if (
            professional is None
            or professional.salon_id != salon.id
            or not professional.is_active
            or professional.role not in (UserRoleChoices.PROFISSIONAL, UserRoleChoices.GESTOR)
        ):
            raise ValidationError(
                {'professional': 'Profissional inválido, inativo ou pertencente a outro salão.'}
            )
        if service is None or service.salon_id != salon.id or not service.is_active:
            raise ValidationError({'service': 'Serviço inválido, inativo ou pertencente a outro salão.'})
        if (
            service.professionals.exists()
            and not service.professionals.filter(pk=professional.pk).exists()
        ):
            raise ValidationError(
                {
                    'professional': (
                        f'O profissional {professional.full_name} não está habilitado '
                        f'para o serviço "{service.name}".'
                    )
                }
            )

    @classmethod
    def recalculate_totals(cls, order: ServiceOrder) -> ServiceOrder:
        subtotal_services = sum(
            (item.net_price for item in order.service_items.all()), ZERO
        )
        subtotal_products = sum(
            (item.total_price for item in order.product_items.all()), ZERO
        )
        gross_total = to_money(subtotal_services) + to_money(subtotal_products)
        discount = to_money(order.discount_amount)
        surcharge = to_money(order.surcharge_amount)
        if discount > gross_total:
            raise ValidationError(
                {'discount_amount': 'O desconto geral não pode ser maior que a soma dos itens da comanda.'}
            )
        order.subtotal_services = to_money(subtotal_services)
        order.subtotal_products = to_money(subtotal_products)
        order.discount_amount = discount
        order.surcharge_amount = surcharge
        order.total_amount = to_money(gross_total - discount + surcharge)
        order.save(
            update_fields=[
                'subtotal_services',
                'subtotal_products',
                'discount_amount',
                'surcharge_amount',
                'total_amount',
                'updated_at',
            ]
        )
        return order

    # ---------------------------------------------------------------- abertura
    @classmethod
    def open_order(cls, *, salon, client=None, opened_by=None, notes: str = '') -> ServiceOrder:
        if client is not None and (client.salon_id != salon.id or not client.is_active):
            raise ValidationError({'client': 'Cliente inválido, inativo ou pertencente a outro salão.'})
        order = ServiceOrder(
            salon=salon,
            client=client,
            opened_by=opened_by,
            notes=(notes or '').strip(),
        )
        order.full_clean()
        order.save()
        return order

    @classmethod
    def open_order_from_appointment(cls, *, salon, appointment, opened_by=None) -> ServiceOrder:
        if appointment is None or appointment.salon_id != salon.id:
            raise ValidationError('Agendamento inválido para este salão.')
        if appointment.status not in APPOINTMENT_STATUSES_ALLOWED_FOR_ORDER:
            raise ValidationError(
                'Somente agendamentos "Em atendimento" ou "Concluído" podem originar uma comanda.'
            )
        with transaction.atomic():
            existing = (
                ServiceOrder.objects.for_salon(salon)
                .select_for_update()
                .filter(appointment=appointment)
                .exclude(status=ServiceOrderStatusChoices.CANCELLED)
                .first()
            )
            if existing is not None:
                raise ValidationError(
                    f'O agendamento já possui a comanda #{existing.pk} ({existing.get_status_display()}).'
                )
            order = ServiceOrder(
                salon=salon,
                appointment=appointment,
                client=appointment.client,
                opened_by=opened_by,
                notes=appointment.notes,
            )
            order.full_clean()
            order.save()
            for appt_item in appointment.items.select_related('service'):
                item = OrderServiceItem(
                    salon=salon,
                    order=order,
                    service=appt_item.service,
                    professional=appointment.professional,
                    gross_price=to_money(appt_item.price_snapshot),
                    discount_amount=ZERO,
                    net_price=to_money(appt_item.price_snapshot),
                )
                item.full_clean()
                item.save()
            return cls.recalculate_totals(order)

    # ---------------------------------------------------------------- itens de serviço
    @classmethod
    def add_service_item(
        cls,
        *,
        order: ServiceOrder,
        service,
        professional,
        gross_price=None,
        discount_amount=ZERO,
    ) -> OrderServiceItem:
        with transaction.atomic():
            locked = cls._lock_open_order(order)
            salon = locked.salon
            cls._validate_professional_for_service(salon, professional, service)
            gross = to_money(service.base_price if gross_price in (None, '') else gross_price)
            discount = to_money(discount_amount)
            if gross < ZERO or discount < ZERO:
                raise ValidationError('Valores do item de serviço não podem ser negativos.')
            item = OrderServiceItem(
                salon=salon,
                order=locked,
                service=service,
                professional=professional,
                gross_price=gross,
                discount_amount=discount,
                net_price=to_money(gross - discount),
            )
            item.full_clean()
            item.save()
            cls.recalculate_totals(locked)
            return item

    @classmethod
    def remove_service_item(cls, *, order: ServiceOrder, item_id: int) -> ServiceOrder:
        with transaction.atomic():
            locked = cls._lock_open_order(order)
            deleted, _ = OrderServiceItem.objects.filter(
                pk=item_id, order=locked, salon=locked.salon
            ).delete()
            if not deleted:
                raise ValidationError('Item de serviço não encontrado nesta comanda.')
            return cls.recalculate_totals(locked)

    # ---------------------------------------------------------------- itens de produto
    @classmethod
    def add_product_item(
        cls,
        *,
        order: ServiceOrder,
        product,
        quantity: int,
        unit_price=None,
    ) -> OrderProductItem:
        quantity = int(quantity or 0)
        if quantity <= 0:
            raise ValidationError({'quantity': 'A quantidade deve ser maior que zero.'})
        with transaction.atomic():
            locked = cls._lock_open_order(order)
            salon = locked.salon
            if product is None or product.salon_id != salon.id:
                raise ValidationError({'product': 'Produto inválido ou pertencente a outro salão.'})
            locked_product = Product.objects.select_for_update().get(pk=product.pk, salon=salon)
            if not locked_product.is_active or not locked_product.is_sellable:
                raise ValidationError(
                    {'product': f'O produto "{locked_product.name}" não está ativo ou não é destinado à venda.'}
                )

            item = OrderProductItem.objects.filter(order=locked, product=locked_product).first()
            new_quantity = quantity + (item.quantity if item else 0)
            # Verificação preliminar de saldo; a baixa definitiva e o bloqueio final ocorrem no
            # fechamento atômico da comanda (Sprint 07 — OrderCheckoutService).
            if new_quantity > locked_product.current_stock:
                raise ValidationError(
                    {
                        'quantity': (
                            f'Saldo insuficiente para "{locked_product.name}": disponível '
                            f'{locked_product.current_stock}, solicitado na comanda {new_quantity}.'
                        )
                    }
                )
            price = to_money(
                locked_product.sale_price if unit_price in (None, '') else unit_price
            )
            if item is None:
                item = OrderProductItem(
                    salon=salon,
                    order=locked,
                    product=locked_product,
                    quantity=new_quantity,
                    unit_price=price,
                    total_price=to_money(price * new_quantity),
                )
            else:
                item.quantity = new_quantity
                item.unit_price = price
                item.total_price = to_money(price * new_quantity)
            item.full_clean()
            item.save()
            cls.recalculate_totals(locked)
            return item

    @classmethod
    def remove_product_item(cls, *, order: ServiceOrder, item_id: int) -> ServiceOrder:
        with transaction.atomic():
            locked = cls._lock_open_order(order)
            deleted, _ = OrderProductItem.objects.filter(
                pk=item_id, order=locked, salon=locked.salon
            ).delete()
            if not deleted:
                raise ValidationError('Item de produto não encontrado nesta comanda.')
            return cls.recalculate_totals(locked)

    # ---------------------------------------------------------------- ajustes e cancelamento
    @classmethod
    def apply_adjustments(cls, *, order: ServiceOrder, discount_amount=ZERO, surcharge_amount=ZERO) -> ServiceOrder:
        discount = to_money(discount_amount)
        surcharge = to_money(surcharge_amount)
        if discount < ZERO or surcharge < ZERO:
            raise ValidationError('Desconto e acréscimo não podem ser negativos.')
        with transaction.atomic():
            locked = cls._lock_open_order(order)
            locked.discount_amount = discount
            locked.surcharge_amount = surcharge
            return cls.recalculate_totals(locked)

    @classmethod
    def cancel_order(cls, *, order: ServiceOrder, reason: str) -> ServiceOrder:
        reason_clean = (reason or '').strip()
        if not reason_clean:
            raise ValidationError({'cancellation_reason': 'Informe o motivo do cancelamento da comanda.'})
        with transaction.atomic():
            locked = cls._lock_open_order(order)
            locked.status = ServiceOrderStatusChoices.CANCELLED
            locked.cancellation_reason = reason_clean
            locked.cancelled_at = timezone.now()
            locked.save(update_fields=['status', 'cancellation_reason', 'cancelled_at', 'updated_at'])
            return locked
