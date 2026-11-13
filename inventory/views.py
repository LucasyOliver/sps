from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, ListView, UpdateView
from base.mixins import GestorRequiredMixin, RecepcaoOrGestorMixin
from inventory.forms import ProductForm, StockMovementForm
from inventory.models import Product, StockMovement, StockMovementTypeChoices
from inventory.services import StockService


def attach_validation_error(form, exc: ValidationError):
    if hasattr(exc, 'message_dict'):
        for field_name, messages_list in exc.message_dict.items():
            target_field = field_name if field_name in form.fields else None
            for msg in messages_list:
                form.add_error(target_field, msg)
    else:
        for msg in exc.messages:
            form.add_error(None, msg)


class ProductListView(RecepcaoOrGestorMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        usage = self.request.GET.get('usage', '').strip()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(sku__icontains=query))
        if usage:
            qs = qs.filter(usage_type=usage)
        if self.request.GET.get('low_stock') == '1':
            qs = qs.filter(current_stock__lte=F('min_stock_alert'))
        return qs.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['low_stock_products'] = StockService.low_stock_products(self.request.salon)
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['selected_usage'] = self.request.GET.get('usage', '').strip()
        context['low_stock_only'] = self.request.GET.get('low_stock') == '1'
        context['usage_choices'] = Product._meta.get_field('usage_type').choices
        return context


class ProductCreateView(GestorRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('inventory:product_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        initial_stock = form.cleaned_data.get('initial_stock') or 0
        with transaction.atomic():
            self.object = form.save()
            if initial_stock > 0:
                StockService.register_movement(
                    salon=self.request.salon,
                    product=self.object,
                    movement_type=StockMovementTypeChoices.PURCHASE_IN,
                    quantity=initial_stock,
                    actor=self.request.user,
                    reason='Saldo inicial informado no cadastro do produto.',
                )
        messages.success(self.request, 'Produto cadastrado com sucesso.')
        return redirect(self.get_success_url())


class ProductUpdateView(GestorRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('inventory:product_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Produto atualizado com sucesso.')
        return super().form_valid(form)


class StockMovementListView(RecepcaoOrGestorMixin, ListView):
    model = StockMovement
    template_name = 'inventory/stock_movement_list.html'
    context_object_name = 'movements'
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().select_related('product', 'actor', 'order')
        product_id = self.request.GET.get('product', '').strip()
        if product_id.isdigit():
            qs = qs.filter(product_id=int(product_id))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.for_salon(self.request.salon).order_by('name')
        context['selected_product'] = self.request.GET.get('product', '').strip()
        return context


class StockMovementCreateView(GestorRequiredMixin, FormView):
    form_class = StockMovementForm
    template_name = 'inventory/stock_movement_form.html'
    success_url = reverse_lazy('inventory:movement_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        product_id = self.request.GET.get('product', '').strip()
        if product_id.isdigit():
            initial['product'] = int(product_id)
        return initial

    def form_valid(self, form):
        try:
            movement = StockService.register_movement(
                salon=self.request.salon,
                product=form.cleaned_data['product'],
                movement_type=form.cleaned_data['movement_type'],
                quantity=form.cleaned_data['quantity'],
                actor=self.request.user,
                reason=form.cleaned_data.get('reason', ''),
            )
        except ValidationError as exc:
            attach_validation_error(form, exc)
            return self.form_invalid(form)

        messages.success(
            self.request,
            f'Movimentação registrada. Novo saldo de "{movement.product.name}": {movement.balance_after}.',
        )
        return redirect(self.get_success_url())
