from datetime import date
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView
from accounts.models import User, UserRoleChoices
from base.mixins import GestorRequiredMixin, SalonTenantRequiredMixin
from finance.models import CashRegisterSession, CommissionEntry
from inventory.models import Product, StockMovement
from reports.pdf_generators import (
    generate_cash_closing_pdf,
    generate_commissions_pdf,
    generate_inventory_pdf,
)
from reports.services import DashboardAnalyticsService


def _parse_optional_date(raw_str: str) -> date | None:
    if not raw_str:
        return None
    try:
        return date.fromisoformat(raw_str.strip())
    except ValueError:
        return None


class ManagerialDashboardView(GestorRequiredMixin, TemplateView):
    template_name = 'reports/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start_date = _parse_optional_date(self.request.GET.get('start_date', ''))
        end_date = _parse_optional_date(self.request.GET.get('end_date', ''))
        metrics = DashboardAnalyticsService.get_salon_metrics(
            salon=self.request.salon,
            start_date=start_date,
            end_date=end_date,
        )
        context.update(metrics)
        context['start_date'] = start_date
        context['end_date'] = end_date
        context['professionals'] = User.objects.filter(
            salon=self.request.salon,
            is_active=True,
            role__in=[UserRoleChoices.PROFISSIONAL, UserRoleChoices.GESTOR],
        ).order_by('full_name')
        return context


class CommissionReportPdfView(SalonTenantRequiredMixin, View):
    """
    Exportação privada de PDF de Extrato de Comissões (S08-T04, RF-011, SEC-E).
    - Gestor: pode exportar de qualquer profissional do próprio salão (ou geral).
    - Profissional: pode exportar EXCLUSIVAMENTE o próprio extrato; se tentar
      informar professional_id de outro profissional ou outro salão, recebe 403.
    - Recepcionista: sem permissão para relatório de comissões (403).
    """

    allowed_roles = {UserRoleChoices.GESTOR, UserRoleChoices.PROFISSIONAL}

    def get(self, request):
        salon = request.salon
        requested_salon_id = request.GET.get('salon', '').strip()
        if requested_salon_id and str(salon.pk) != requested_salon_id:
            raise PermissionDenied('Acesso negado a relatório de outro salão.')

        prof_param = request.GET.get('professional', '').strip()
        target_prof = None

        if request.user.role == UserRoleChoices.PROFISSIONAL:
            if prof_param and (
                not prof_param.isdigit() or int(prof_param) != request.user.pk
            ):
                raise PermissionDenied(
                    'Profissional só possui permissão para exportar o próprio demonstrativo de comissões.'
                )
            target_prof = request.user
        else:
            if prof_param:
                if not prof_param.isdigit():
                    raise PermissionDenied('Profissional inválido.')
                target_prof = User.objects.filter(pk=int(prof_param)).first()
                if target_prof is None or target_prof.salon_id != salon.id:
                    raise PermissionDenied(
                        'Profissional informado não pertence a este salão.'
                    )

        qs = CommissionEntry.objects.for_salon(salon).select_related(
            'professional',
            'order',
            'order_service_item__service',
        )
        if target_prof is not None:
            qs = qs.filter(professional=target_prof)

        start_date = _parse_optional_date(request.GET.get('start_date', ''))
        end_date = _parse_optional_date(request.GET.get('end_date', ''))
        if start_date is not None:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date is not None:
            qs = qs.filter(created_at__date__lte=end_date)

        pdf_bytes = generate_commissions_pdf(
            salon=salon,
            entries=list(qs),
            professional=target_prof,
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="extrato_comissoes_{salon.slug}.pdf"'
        )
        return response


class CashClosingReportPdfView(SalonTenantRequiredMixin, View):
    """
    Exportação privada de PDF de Fechamento de Caixa (S08-T04, RF-011, SEC-E).
    Permitido apenas a Gestor e Recepcionista do salão proprietário da sessão.
    Retorna 403 Forbidden para Profissional ou quando a sessão pertence a outro salão.
    """

    allowed_roles = {UserRoleChoices.GESTOR, UserRoleChoices.RECEPCIONISTA}

    def get(self, request, session_pk: int):
        session = (
            CashRegisterSession.objects.select_related('salon', 'opened_by', 'closed_by')
            .prefetch_related('transactions')
            .filter(pk=session_pk)
            .first()
        )
        if session is None or session.salon_id != request.salon.id:
            raise PermissionDenied(
                'Sessão de caixa inexistente ou pertencente a outro salão.'
            )

        pdf_bytes = generate_cash_closing_pdf(
            salon=request.salon,
            cash_session=session,
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="fechamento_caixa_{session.pk}_{request.salon.slug}.pdf"'
        )
        return response


class InventoryReportPdfView(GestorRequiredMixin, View):
    """
    Exportação privada de PDF de Posição e Movimentação de Estoque (S08-T04, RF-011, SEC-E).
    Exclusivo do Gestor do salão.
    """

    def get(self, request):
        salon = request.salon
        requested_salon_id = request.GET.get('salon', '').strip()
        if requested_salon_id and str(salon.pk) != requested_salon_id:
            raise PermissionDenied('Acesso negado ao relatório de estoque de outro salão.')

        products = list(Product.objects.for_salon(salon).order_by('name'))
        movements = list(
            StockMovement.objects.for_salon(salon)
            .select_related('product', 'actor')
            .order_by('-created_at')[:50]
        )
        pdf_bytes = generate_inventory_pdf(
            salon=salon,
            products=products,
            movements=movements,
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="posicao_estoque_{salon.slug}.pdf"'
        )
        return response
