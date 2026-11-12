from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from catalog.models import ProfessionalServiceCommission


TWO_PLACES = Decimal('0.01')


def resolve_commission_percentage(salon, professional, service) -> Decimal:
    """
    Retorna o percentual de comissão aplicável para (salon, professional, service).
    Precedência (RF-003):
      1. Regra ativa em ProfessionalServiceCommission para (salon, professional, service).
      2. Percentual padrão do serviço (Service.default_commission_pct).
    """
    if salon is None or professional is None or service is None:
        raise ValidationError(
            'Salão, profissional e serviço são obrigatórios para resolver a comissão.'
        )

    salon_id = getattr(salon, 'pk', salon)
    if professional.salon_id != salon_id:
        raise ValidationError(
            'Profissional informado não pertence ao salão da operação.'
        )
    if service.salon_id != salon_id:
        raise ValidationError(
            'Serviço informado não pertence ao salão da operação.'
        )

    specific_rule = (
        ProfessionalServiceCommission.objects.for_salon(salon_id)
        .filter(
            professional=professional,
            service=service,
            is_active=True,
        )
        .first()
    )
    if specific_rule is not None:
        return specific_rule.commission_pct.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    return service.default_commission_pct.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calculate_commission_amount(base_amount: Decimal, commission_pct: Decimal) -> Decimal:
    """Calcula o valor monetário da comissão com arredondamento financeiro ROUND_HALF_UP."""
    base = Decimal(str(base_amount))
    pct = Decimal(str(commission_pct))
    raw_value = (base * pct) / Decimal('100.00')
    return raw_value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
