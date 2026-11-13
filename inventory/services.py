from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from inventory.models import (
    INTERNAL_USAGE_TYPES,
    Product,
    StockMovement,
    StockMovementTypeChoices,
)


class InsufficientStockError(ValidationError):
    """Saldo insuficiente para concluir a saída de estoque solicitada (RF-008)."""


INBOUND_TYPES = {
    StockMovementTypeChoices.PURCHASE_IN,
    StockMovementTypeChoices.ORDER_REVERSAL,
}
OUTBOUND_TYPES = {
    StockMovementTypeChoices.SALE_OUT,
    StockMovementTypeChoices.INTERNAL_OUT,
}
MANUAL_MOVEMENT_TYPES = {
    StockMovementTypeChoices.PURCHASE_IN,
    StockMovementTypeChoices.INTERNAL_OUT,
    StockMovementTypeChoices.ADJUSTMENT,
}


class StockService:
    """
    Serviço transacional do livro razão de estoque (S06-T02, RF-008, RNF-002).
    Toda alteração de saldo passa por aqui: bloqueia o produto com select_for_update(),
    impede saldo negativo e grava StockMovement imutável com o saldo resultante.
    """

    @staticmethod
    def _signed_delta(movement_type: str, quantity: int) -> int:
        if movement_type in INBOUND_TYPES:
            if quantity <= 0:
                raise ValidationError({'quantity': 'A quantidade de entrada deve ser maior que zero.'})
            return quantity
        if movement_type in OUTBOUND_TYPES:
            if quantity <= 0:
                raise ValidationError({'quantity': 'A quantidade de saída deve ser maior que zero.'})
            return -quantity
        if movement_type == StockMovementTypeChoices.ADJUSTMENT:
            if quantity == 0:
                raise ValidationError(
                    {'quantity': 'O ajuste de inventário deve ser diferente de zero (positivo ou negativo).'}
                )
            return quantity
        raise ValidationError({'movement_type': 'Tipo de movimentação de estoque inválido.'})

    @classmethod
    def register_movement(
        cls,
        *,
        salon,
        product,
        movement_type: str,
        quantity: int,
        actor=None,
        reason: str = '',
        order=None,
    ) -> StockMovement:
        if salon is None or product is None or product.salon_id != salon.id:
            raise ValidationError({'product': 'Produto inválido ou pertencente a outro salão.'})
        if order is not None and order.salon_id != salon.id:
            raise ValidationError({'order': 'Comanda vinculada pertence a outro salão.'})
        if actor is not None and actor.salon_id not in (None, salon.id):
            raise ValidationError('Responsável pela movimentação pertence a outro salão.')

        quantity = int(quantity)
        delta = cls._signed_delta(movement_type, quantity)
        reason_clean = (reason or '').strip()

        if movement_type == StockMovementTypeChoices.ADJUSTMENT and not reason_clean:
            raise ValidationError({'reason': 'Informe o motivo do ajuste de inventário (auditoria).'})

        with transaction.atomic():
            locked = Product.objects.select_for_update().get(pk=product.pk, salon=salon)

            if (
                movement_type == StockMovementTypeChoices.INTERNAL_OUT
                and locked.usage_type not in INTERNAL_USAGE_TYPES
            ):
                raise ValidationError(
                    {'movement_type': f'O produto "{locked.name}" não está habilitado para consumo interno.'}
                )

            new_balance = locked.current_stock + delta
            if new_balance < 0:
                raise InsufficientStockError(
                    {
                        'quantity': (
                            f'Saldo insuficiente para "{locked.name}": saldo atual '
                            f'{locked.current_stock} {locked.unit}, saída solicitada {abs(delta)}. '
                            f'O estoque não pode ficar negativo.'
                        )
                    }
                )

            Product.objects.filter(pk=locked.pk).update(current_stock=F('current_stock') + delta)
            locked.refresh_from_db(fields=['current_stock'])

            movement = StockMovement(
                salon=salon,
                product=locked,
                movement_type=movement_type,
                quantity_delta=delta,
                balance_after=locked.current_stock,
                order=order,
                actor=actor,
                reason=reason_clean,
            )
            movement.full_clean()
            movement.save()

        product.current_stock = locked.current_stock
        return movement

    @staticmethod
    def low_stock_products(salon):
        """Produtos ativos com saldo atual menor ou igual ao estoque mínimo (alerta de reposição)."""
        return (
            Product.objects.for_salon(salon)
            .filter(is_active=True, current_stock__lte=F('min_stock_alert'))
            .order_by('current_stock', 'name')
        )
