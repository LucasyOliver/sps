from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView, TemplateView
from accounts.models import User, UserRoleChoices
from base.mixins import (
    GestorRequiredMixin,
    ProfissionalScopeMixin,
    RecepcaoOrGestorMixin,
)
from finance.forms import (
    CashSessionCloseForm,
    CashSessionOpenForm,
    ManualCashTransactionForm,
    OrderCheckoutForm,
    OrderReversalForm,
)
from finance.models import (
    CashRegisterSession,
    CommissionEntry,
    CommissionStatusChoices,
)
from finance.services import (
    CashRegisterService,
    CommissionService,
    OrderCheckoutService,
)
from orders.models import ServiceOrder


def _extract_error_messages(exc: ValidationError) -> list[str]:
    if hasattr(exc, 'message_dict'):
        return [msg for msgs in exc.message_dict.values() for msg in msgs]
    return list(exc.messages)


class CashRegisterDashboardView(RecepcaoOrGestorMixin, TemplateView):
    template_name = 'finance/cash_register_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        salon = self.request.salon
        open_session = CashRegisterService.get_open_session(salon)
        context['open_session'] = open_session
        context['open_form'] = CashSessionOpenForm()
        context['manual_tx_form'] = ManualCashTransactionForm()
        if open_session is not None:
            expected = open_session.calculate_expected_balance()
            context['expected_balance'] = expected
            context['close_form'] = CashSessionCloseForm(
                initial={'closing_balance_counted': expected}
            )
            context['session_transactions'] = open_session.transactions.select_related(
                'order', 'created_by'
            )
        context['recent_sessions'] = (
            CashRegisterSession.objects.for_salon(salon)
            .select_related('opened_by', 'closed_by')[:15]
        )
        return context


class CashSessionOpenView(RecepcaoOrGestorMixin, FormView):
    form_class = CashSessionOpenForm
    template_name = 'finance/cash_register_dashboard.html'
    success_url = reverse_lazy('finance:cash_dashboard')

    def form_valid(self, form):
        try:
            session = CashRegisterService.open_session(
                salon=self.request.salon,
                opened_by=self.request.user,
                opening_balance=form.cleaned_data['opening_balance'],
                notes=form.cleaned_data.get('notes', ''),
            )
        except ValidationError as exc:
            for msg in _extract_error_messages(exc):
                messages.error(self.request, msg)
            return redirect(self.success_url)

        messages.success(
            self.request,
            f'Caixa #{session.pk} aberto com saldo inicial de R$ {session.opening_balance}.',
        )
        return redirect(self.success_url)


class CashSessionCloseView(RecepcaoOrGestorMixin, FormView):
    form_class = CashSessionCloseForm
    template_name = 'finance/cash_register_dashboard.html'
    success_url = reverse_lazy('finance:cash_dashboard')

    def form_valid(self, form):
        try:
            session = CashRegisterService.close_session(
                salon=self.request.salon,
                closed_by=self.request.user,
                closing_balance_counted=form.cleaned_data['closing_balance_counted'],
                notes=form.cleaned_data.get('notes', ''),
            )
        except ValidationError as exc:
            for msg in _extract_error_messages(exc):
                messages.error(self.request, msg)
            return redirect(self.success_url)

        messages.success(
            self.request,
            f'Caixa #{session.pk} fechado com sucesso (esperado: R$ {session.closing_balance_expected}, '
            f'conferido: R$ {session.closing_balance_counted}).',
        )
        return redirect(self.success_url)


class ManualCashTransactionCreateView(RecepcaoOrGestorMixin, FormView):
    form_class = ManualCashTransactionForm
    template_name = 'finance/cash_register_dashboard.html'
    success_url = reverse_lazy('finance:cash_dashboard')

    def form_valid(self, form):
        try:
            CashRegisterService.record_manual_transaction(
                salon=self.request.salon,
                transaction_type=form.cleaned_data['transaction_type'],
                amount=form.cleaned_data['amount'],
                description=form.cleaned_data['description'],
                payment_method=form.cleaned_data['payment_method'],
                actor=self.request.user,
            )
        except ValidationError as exc:
            for msg in _extract_error_messages(exc):
                messages.error(self.request, msg)
            return redirect(self.success_url)

        messages.success(self.request, 'Lançamento registrado no caixa diário.')
        return redirect(self.success_url)


class OrderCheckoutView(RecepcaoOrGestorMixin, View):
    http_method_names = ['post']

    def post(self, request, order_pk):
        order = get_object_or_404(
            ServiceOrder.objects.for_salon(request.salon),
            pk=order_pk,
        )
        detail_url = reverse('orders:order_detail', args=[order.pk])
        form = OrderCheckoutForm(data=request.POST)
        if not form.is_valid():
            for field, errors in form.errors.items():
                label = form.fields[field].label if field in form.fields else ''
                for msg in errors:
                    messages.error(request, f'{label}: {msg}' if label else msg)
            return redirect(detail_url)

        try:
            OrderCheckoutService.close_and_pay_order(
                salon=request.salon,
                order=order,
                payments=form.to_payments_list(),
                actor=request.user,
            )
        except ValidationError as exc:
            for msg in _extract_error_messages(exc):
                messages.error(request, msg)
            return redirect(detail_url)

        messages.success(
            request,
            f'Comanda #{order.pk} fechada e paga com sucesso! Estoque, caixa, comissões e registro fiscal atualizados.',
        )
        return redirect(detail_url)


class OrderReversalView(GestorRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, order_pk):
        order = get_object_or_404(
            ServiceOrder.objects.for_salon(request.salon),
            pk=order_pk,
        )
        detail_url = reverse('orders:order_detail', args=[order.pk])
        form = OrderReversalForm(data=request.POST)
        if not form.is_valid():
            for msg in form.errors.get('reason', []):
                messages.error(request, msg)
            return redirect(detail_url)

        try:
            OrderCheckoutService.reverse_paid_order(
                salon=request.salon,
                order=order,
                actor=request.user,
                reason=form.cleaned_data['reason'],
            )
        except ValidationError as exc:
            for msg in _extract_error_messages(exc):
                messages.error(request, msg)
            return redirect(detail_url)

        messages.success(
            request,
            f'Comanda #{order.pk} estornada com sucesso. Caixa, comissões, estoque e registro fiscal foram revertidos.',
        )
        return redirect(detail_url)


class CommissionEntryListView(ProfissionalScopeMixin, ListView):
    model = CommissionEntry
    template_name = 'finance/commission_list.html'
    context_object_name = 'commissions'
    professional_lookup_field = 'professional'
    paginate_by = 50

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related(
                'professional',
                'order',
                'order_service_item__service',
                'paid_by',
            )
        )
        prof_id = self.request.GET.get('professional', '').strip()
        status_filter = self.request.GET.get('status', '').strip()

        if (
            prof_id.isdigit()
            and self.request.user.role != UserRoleChoices.PROFISSIONAL
        ):
            qs = qs.filter(professional_id=int(prof_id))
        if status_filter in CommissionStatusChoices.values:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['total_pending'] = (
            qs.filter(status=CommissionStatusChoices.PENDING).aggregate(
                total=Sum('commission_amount')
            )['total']
            or Decimal('0.00')
        )
        context['total_paid'] = (
            qs.filter(status=CommissionStatusChoices.PAID).aggregate(
                total=Sum('commission_amount')
            )['total']
            or Decimal('0.00')
        )
        context['professionals'] = User.objects.filter(
            salon=self.request.salon,
            is_active=True,
            role__in=[UserRoleChoices.PROFISSIONAL, UserRoleChoices.GESTOR],
        ).order_by('full_name')
        context['status_choices'] = CommissionStatusChoices.choices
        context['selected_professional'] = self.request.GET.get('professional', '').strip()
        context['selected_status'] = self.request.GET.get('status', '').strip()
        return context


class CommissionPayoutView(GestorRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request):
        raw_ids = request.POST.getlist('entry_ids')
        entry_ids = [int(pk) for pk in raw_ids if str(pk).isdigit()]
        try:
            paid_count = CommissionService.pay_commission_entries(
                salon=request.salon,
                entry_ids=entry_ids,
                actor=request.user,
            )
        except ValidationError as exc:
            for msg in _extract_error_messages(exc):
                messages.error(request, msg)
            return redirect(reverse('finance:commission_list'))

        messages.success(
            request,
            f'Repasse registrado para {paid_count} lançamento(s) de comissão.',
        )
        return redirect(reverse('finance:commission_list'))
