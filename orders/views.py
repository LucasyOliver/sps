from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView, ListView
from base.mixins import RecepcaoOrGestorMixin
from orders.forms import (
    OrderAdjustmentForm,
    OrderCancelForm,
    OrderProductItemForm,
    OrderServiceItemForm,
    ServiceOrderCreateForm,
)
from orders.models import ServiceOrder, ServiceOrderStatusChoices
from orders.services import OrderService
from scheduling.models import Appointment


def _error_messages(exc: ValidationError) -> list[str]:
    if hasattr(exc, 'message_dict'):
        return [msg for msgs in exc.message_dict.values() for msg in msgs]
    return list(exc.messages)


def _order_detail_url(order) -> str:
    return reverse('orders:order_detail', args=[order.pk])


class ServiceOrderListView(RecepcaoOrGestorMixin, ListView):
    model = ServiceOrder
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().select_related('client', 'appointment', 'opened_by')
        status = self.request.GET.get('status', ServiceOrderStatusChoices.OPEN).strip()
        if status in ServiceOrderStatusChoices.values:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_status'] = self.request.GET.get('status', ServiceOrderStatusChoices.OPEN).strip()
        context['status_choices'] = ServiceOrderStatusChoices.choices
        return context


class ServiceOrderCreateView(RecepcaoOrGestorMixin, FormView):
    form_class = ServiceOrderCreateForm
    template_name = 'orders/order_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        try:
            order = OrderService.open_order(
                salon=self.request.salon,
                client=form.cleaned_data.get('client'),
                opened_by=self.request.user,
                notes=form.cleaned_data.get('notes', ''),
            )
        except ValidationError as exc:
            for msg in _error_messages(exc):
                form.add_error(None, msg)
            return self.form_invalid(form)
        messages.success(self.request, f'Comanda #{order.pk} aberta com sucesso.')
        return redirect(_order_detail_url(order))


class ServiceOrderFromAppointmentView(RecepcaoOrGestorMixin, View):
    http_method_names = ['post']

    def post(self, request, appointment_pk):
        appointment = get_object_or_404(
            Appointment.objects.for_salon(request.salon), pk=appointment_pk
        )
        try:
            order = OrderService.open_order_from_appointment(
                salon=request.salon,
                appointment=appointment,
                opened_by=request.user,
            )
        except ValidationError as exc:
            for msg in _error_messages(exc):
                messages.error(request, msg)
            return redirect(reverse('scheduling:appointment_detail', args=[appointment.pk]))
        messages.success(request, f'Comanda #{order.pk} aberta a partir do agendamento.')
        return redirect(_order_detail_url(order))


class ServiceOrderDetailView(RecepcaoOrGestorMixin, DetailView):
    model = ServiceOrder
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('client', 'appointment', 'opened_by')
            .prefetch_related('service_items__service', 'service_items__professional', 'product_items__product')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        salon = self.request.salon
        context['service_item_form'] = OrderServiceItemForm(salon=salon)
        context['product_item_form'] = OrderProductItemForm(salon=salon)
        context['adjustment_form'] = OrderAdjustmentForm(
            initial={
                'discount_amount': self.object.discount_amount,
                'surcharge_amount': self.object.surcharge_amount,
            }
        )
        context['cancel_form'] = OrderCancelForm()
        return context


class BaseOrderActionView(RecepcaoOrGestorMixin, View):
    """Ações POST sobre uma comanda do próprio salão (404 para comandas de outro salão)."""

    http_method_names = ['post']
    form_class = None
    success_message = ''

    def get_order(self, request, pk):
        return get_object_or_404(ServiceOrder.objects.for_salon(request.salon), pk=pk)

    def perform(self, order, form, **kwargs):
        raise NotImplementedError

    def post(self, request, pk, **kwargs):
        order = self.get_order(request, pk)
        form = None
        if self.form_class is not None:
            form_kwargs = {'data': request.POST}
            if self.form_class in (OrderServiceItemForm, OrderProductItemForm):
                form_kwargs['salon'] = request.salon
            form = self.form_class(**form_kwargs)
            if not form.is_valid():
                for field, errors in form.errors.items():
                    label = form.fields[field].label if field in form.fields else ''
                    for msg in errors:
                        messages.error(request, f'{label}: {msg}' if label else msg)
                return redirect(_order_detail_url(order))
        try:
            self.perform(order, form, **kwargs)
        except ValidationError as exc:
            for msg in _error_messages(exc):
                messages.error(request, msg)
            return redirect(_order_detail_url(order))
        messages.success(request, self.success_message)
        return redirect(_order_detail_url(order))


class OrderAddServiceItemView(BaseOrderActionView):
    form_class = OrderServiceItemForm
    success_message = 'Serviço adicionado à comanda.'

    def perform(self, order, form, **kwargs):
        OrderService.add_service_item(
            order=order,
            service=form.cleaned_data['service'],
            professional=form.cleaned_data['professional'],
            gross_price=form.cleaned_data.get('gross_price'),
            discount_amount=form.cleaned_data.get('discount_amount') or 0,
        )


class OrderRemoveServiceItemView(BaseOrderActionView):
    success_message = 'Serviço removido da comanda.'

    def perform(self, order, form, item_pk=None, **kwargs):
        OrderService.remove_service_item(order=order, item_id=item_pk)


class OrderAddProductItemView(BaseOrderActionView):
    form_class = OrderProductItemForm
    success_message = 'Produto adicionado à comanda.'

    def perform(self, order, form, **kwargs):
        OrderService.add_product_item(
            order=order,
            product=form.cleaned_data['product'],
            quantity=form.cleaned_data['quantity'],
            unit_price=form.cleaned_data.get('unit_price'),
        )


class OrderRemoveProductItemView(BaseOrderActionView):
    success_message = 'Produto removido da comanda.'

    def perform(self, order, form, item_pk=None, **kwargs):
        OrderService.remove_product_item(order=order, item_id=item_pk)


class OrderAdjustmentView(BaseOrderActionView):
    form_class = OrderAdjustmentForm
    success_message = 'Desconto e acréscimo da comanda atualizados.'

    def perform(self, order, form, **kwargs):
        OrderService.apply_adjustments(
            order=order,
            discount_amount=form.cleaned_data['discount_amount'],
            surcharge_amount=form.cleaned_data['surcharge_amount'],
        )


class OrderCancelView(BaseOrderActionView):
    form_class = OrderCancelForm
    success_message = 'Comanda cancelada.'

    def perform(self, order, form, **kwargs):
        OrderService.cancel_order(order=order, reason=form.cleaned_data['cancellation_reason'])
