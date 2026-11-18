from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum
from finance.models import (
    CashRegisterSession,
    CommissionEntry,
    CommissionStatusChoices,
)
from inventory.services import StockService
from orders.models import ServiceOrder, ServiceOrderStatusChoices
from scheduling.models import Appointment, AppointmentStatusChoices

TWO_PLACES = Decimal('0.01')
ZERO = Decimal('0.00')


class DashboardAnalyticsService:
    """
    Serviço consolidador de indicadores do Dashboard Gerencial por salão
    (S08-T03, RF-011, RNF-001).
    """

    @staticmethod
    def get_salon_metrics(
        *,
        salon,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        orders_qs = ServiceOrder.objects.for_salon(salon)
        commissions_qs = CommissionEntry.objects.for_salon(salon)
        appointments_qs = Appointment.objects.for_salon(salon)

        if start_date is not None:
            orders_qs = orders_qs.filter(created_at__date__gte=start_date)
            commissions_qs = commissions_qs.filter(created_at__date__gte=start_date)
            appointments_qs = appointments_qs.filter(start_at__date__gte=start_date)
        if end_date is not None:
            orders_qs = orders_qs.filter(created_at__date__lte=end_date)
            commissions_qs = commissions_qs.filter(created_at__date__lte=end_date)
            appointments_qs = appointments_qs.filter(start_at__date__lte=end_date)

        paid_orders = orders_qs.filter(status=ServiceOrderStatusChoices.CLOSED_PAID)
        paid_orders_count = paid_orders.count()
        open_orders_count = orders_qs.filter(status=ServiceOrderStatusChoices.OPEN).count()

        totals = paid_orders.aggregate(
            services_sum=Sum('subtotal_services'),
            products_sum=Sum('subtotal_products'),
            net_sum=Sum('total_amount'),
        )
        subtotal_services = totals['services_sum'] or ZERO
        subtotal_products = totals['products_sum'] or ZERO
        gross_revenue = (subtotal_services + subtotal_products).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        net_revenue = (totals['net_sum'] or ZERO).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        if paid_orders_count > 0:
            average_ticket = (net_revenue / Decimal(paid_orders_count)).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP
            )
        else:
            average_ticket = ZERO

        comm_pending = (
            commissions_qs.filter(status=CommissionStatusChoices.PENDING).aggregate(
                total=Sum('commission_amount')
            )['total']
            or ZERO
        )
        comm_paid = (
            commissions_qs.filter(status=CommissionStatusChoices.PAID).aggregate(
                total=Sum('commission_amount')
            )['total']
            or ZERO
        )

        completed_count = appointments_qs.filter(
            status=AppointmentStatusChoices.COMPLETED
        ).count()
        no_show_count = appointments_qs.filter(
            status=AppointmentStatusChoices.NO_SHOW
        ).count()
        cancelled_count = appointments_qs.filter(
            status=AppointmentStatusChoices.CANCELLED
        ).count()
        total_appointments = appointments_qs.count()

        evaluated_attendance = completed_count + no_show_count
        if evaluated_attendance > 0:
            attendance_rate_pct = (
                (Decimal(completed_count) * Decimal('100.00'))
                / Decimal(evaluated_attendance)
            ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            no_show_rate_pct = (
                (Decimal(no_show_count) * Decimal('100.00'))
                / Decimal(evaluated_attendance)
            ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        else:
            attendance_rate_pct = Decimal('100.00')
            no_show_rate_pct = ZERO

        low_stock_list = list(StockService.low_stock_products(salon))
        recent_cash_sessions = list(
            CashRegisterSession.objects.for_salon(salon).select_related(
                'opened_by', 'closed_by'
            )[:10]
        )

        return {
            'gross_revenue': gross_revenue,
            'net_revenue': net_revenue,
            'subtotal_services': subtotal_services,
            'subtotal_products': subtotal_products,
            'paid_orders_count': paid_orders_count,
            'open_orders_count': open_orders_count,
            'average_ticket': average_ticket,
            'commissions_pending_total': comm_pending,
            'commissions_paid_total': comm_paid,
            'total_appointments': total_appointments,
            'completed_appointments': completed_count,
            'no_show_appointments': no_show_count,
            'cancelled_appointments': cancelled_count,
            'attendance_rate_pct': attendance_rate_pct,
            'no_show_rate_pct': no_show_rate_pct,
            'low_stock_count': len(low_stock_list),
            'low_stock_products': low_stock_list,
            'recent_cash_sessions': recent_cash_sessions,
        }
