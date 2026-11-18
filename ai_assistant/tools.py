from datetime import date, timedelta
from django.core.exceptions import PermissionDenied
from django.db.models import Max, Q
from django.utils import timezone
from langchain_core.tools import tool
from accounts.models import UserRoleChoices
from clients.models import Client
from inventory.services import StockService
from reports.services import DashboardAnalyticsService
from salons.models import Salon
from scheduling.models import ACTIVE_APPOINTMENT_STATUSES, Appointment


def _assert_authorized_context(salon_id: int, user_role: str, *, require_gestor: bool = False) -> Salon:
    if not salon_id:
        raise PermissionDenied('Contexto de salão ausente para execução da tool.')
    if user_role not in (UserRoleChoices.GESTOR, UserRoleChoices.RECEPCIONISTA):
        raise PermissionDenied('Perfil sem acesso ao Assistente Gerencial Interno.')
    if require_gestor and user_role != UserRoleChoices.GESTOR:
        raise PermissionDenied(
            'Apenas o Gestor do salão possui permissão para consultar faturamento e comissões globais.'
        )
    salon = Salon.objects.filter(pk=salon_id, is_active=True).first()
    if salon is None:
        raise PermissionDenied('Salão inativo ou inexistente.')
    return salon


def get_salon_agenda_summary(
    *,
    salon_id: int,
    user_role: str,
    target_date: str | None = None,
) -> dict:
    """
    Tool somente-leitura: resume agendamentos do salão na data de referência
    estritamente filtrados pelo salon_id fixado pelo servidor autenticado.
    """
    salon = _assert_authorized_context(salon_id, user_role)
    ref_date = timezone.localdate()
    if target_date:
        try:
            ref_date = date.fromisoformat(str(target_date).strip())
        except ValueError:
            pass

    qs = (
        Appointment.objects.for_salon(salon)
        .select_related('client', 'professional')
        .filter(start_at__date=ref_date)
        .order_by('start_at')
    )
    active_list = [
        {
            'appointment_id': appt.pk,
            'start_time': timezone.localtime(appt.start_at).strftime('%H:%M'),
            'end_time': timezone.localtime(appt.end_at).strftime('%H:%M'),
            'client_name': appt.client.full_name,
            'professional_name': appt.professional.full_name,
            'status': appt.get_status_display(),
            'estimated_amount': str(appt.total_estimated_amount),
        }
        for appt in qs
        if appt.status in ACTIVE_APPOINTMENT_STATUSES
    ]
    return {
        'tool': 'get_salon_agenda_summary',
        'salon_id': salon.pk,
        'salon_name': salon.trade_name,
        'reference_date': ref_date.isoformat(),
        'total_appointments_on_date': qs.count(),
        'active_appointments_count': len(active_list),
        'active_appointments': active_list,
    }


def get_revenue_and_commissions_summary(
    *,
    salon_id: int,
    user_role: str,
) -> dict:
    """
    Tool somente-leitura (EXCLUSIVA DO GESTOR): resume faturamento bruto/líquido,
    comandas pagas e comissões pendentes/pagas do salão autenticado.
    """
    salon = _assert_authorized_context(salon_id, user_role, require_gestor=True)
    metrics = DashboardAnalyticsService.get_salon_metrics(salon=salon)
    return {
        'tool': 'get_revenue_and_commissions_summary',
        'salon_id': salon.pk,
        'salon_name': salon.trade_name,
        'gross_revenue': str(metrics['gross_revenue']),
        'net_revenue': str(metrics['net_revenue']),
        'paid_orders_count': metrics['paid_orders_count'],
        'average_ticket': str(metrics['average_ticket']),
        'commissions_pending_total': str(metrics['commissions_pending_total']),
        'commissions_paid_total': str(metrics['commissions_paid_total']),
        'attendance_rate_pct': str(metrics['attendance_rate_pct']),
    }


def get_low_stock_products(
    *,
    salon_id: int,
    user_role: str,
) -> dict:
    """
    Tool somente-leitura: lista produtos ativos com saldo atual igual ou abaixo do
    estoque mínimo no salão autenticado.
    """
    salon = _assert_authorized_context(salon_id, user_role)
    products = list(StockService.low_stock_products(salon))
    return {
        'tool': 'get_low_stock_products',
        'salon_id': salon.pk,
        'salon_name': salon.trade_name,
        'low_stock_count': len(products),
        'products': [
            {
                'product_id': p.pk,
                'name': p.name,
                'sku': p.sku,
                'current_stock': p.current_stock,
                'min_stock_alert': p.min_stock_alert,
                'unit': p.unit,
            }
            for p in products
        ],
    }


def get_inactive_clients(
    *,
    salon_id: int,
    user_role: str,
    days_inactive: int = 60,
) -> dict:
    """
    Tool somente-leitura: retorna clientes ativos do salão sem agendamento nos
    últimos `days_inactive` dias (ou que nunca agendaram).
    """
    salon = _assert_authorized_context(salon_id, user_role)
    cutoff = timezone.now() - timedelta(days=max(1, int(days_inactive or 60)))
    clients_qs = (
        Client.objects.for_salon(salon)
        .filter(is_active=True)
        .annotate(last_appointment_at=Max('appointments__start_at'))
        .filter(
            Q(last_appointment_at__lt=cutoff) | Q(last_appointment_at__isnull=True)
        )
        .order_by('full_name')
    )
    items = [
        {
            'client_id': c.pk,
            'full_name': c.full_name,
            'phone': c.phone,
            'last_appointment_at': (
                timezone.localtime(c.last_appointment_at).strftime('%d/%m/%Y')
                if c.last_appointment_at
                else 'Nunca agendou'
            ),
        }
        for c in clients_qs[:30]
    ]
    return {
        'tool': 'get_inactive_clients',
        'salon_id': salon.pk,
        'salon_name': salon.trade_name,
        'days_inactive_threshold': int(days_inactive or 60),
        'inactive_clients_count': len(items),
        'clients': items,
    }


def build_authorized_tools(*, salon_id: int, user_role: str) -> dict:
    """
    Constrói as tools LangChain com `salon_id` e `user_role` fixados por closure
    no servidor autenticado (RF-012, SEC-G). Nenhuma tool aceita `salon_id` externo.
    """
    _assert_authorized_context(salon_id, user_role)

    @tool('get_salon_agenda_summary')
    def agenda_tool(target_date: str = '') -> dict:
        """Consulta o resumo da agenda do salão autenticado para a data informada."""
        return get_salon_agenda_summary(
            salon_id=salon_id,
            user_role=user_role,
            target_date=target_date or None,
        )

    @tool('get_low_stock_products')
    def low_stock_tool() -> dict:
        """Lista os produtos com estoque baixo no salão autenticado."""
        return get_low_stock_products(salon_id=salon_id, user_role=user_role)

    @tool('get_inactive_clients')
    def inactive_clients_tool(days_inactive: int = 60) -> dict:
        """Lista clientes inativos sem agendamento recente no salão autenticado."""
        return get_inactive_clients(
            salon_id=salon_id,
            user_role=user_role,
            days_inactive=days_inactive,
        )

    tools_map = {
        'get_salon_agenda_summary': agenda_tool,
        'get_low_stock_products': low_stock_tool,
        'get_inactive_clients': inactive_clients_tool,
    }

    if user_role == UserRoleChoices.GESTOR:

        @tool('get_revenue_and_commissions_summary')
        def revenue_tool() -> dict:
            """Consulta o faturamento bruto/líquido e comissões do salão autenticado (exclusivo Gestor)."""
            return get_revenue_and_commissions_summary(
                salon_id=salon_id,
                user_role=user_role,
            )

        tools_map['get_revenue_and_commissions_summary'] = revenue_tool

    return tools_map
