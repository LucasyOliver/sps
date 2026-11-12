from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from accounts.models import UserRoleChoices
from base.mixins import (
    GestorRequiredMixin,
    ProfissionalScopeMixin,
    SalonTenantRequiredMixin,
)
from catalog.forms import (
    ProfessionalServiceCommissionForm,
    ServiceCategoryForm,
    ServiceForm,
)
from catalog.models import ProfessionalServiceCommission, Service, ServiceCategory


class ServiceListView(SalonTenantRequiredMixin, ListView):
    model = Service
    template_name = 'catalog/service_list.html'
    context_object_name = 'services'
    allowed_roles = {
        UserRoleChoices.GESTOR,
        UserRoleChoices.RECEPCIONISTA,
        UserRoleChoices.PROFISSIONAL,
    }

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related('category')
            .prefetch_related('professionals')
        )
        query = self.request.GET.get('q', '').strip()
        category_id = self.request.GET.get('category', '').strip()
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(category__name__icontains=query)
            )
        if category_id.isdigit():
            qs = qs.filter(category_id=int(category_id))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ServiceCategory.objects.for_salon(self.request.salon)
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['selected_category'] = self.request.GET.get('category', '').strip()
        return context


class ServiceCreateView(GestorRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'catalog/service_form.html'
    success_url = reverse_lazy('catalog:service_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Serviço cadastrado com sucesso.')
        return super().form_valid(form)


class ServiceUpdateView(GestorRequiredMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = 'catalog/service_form.html'
    success_url = reverse_lazy('catalog:service_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Serviço atualizado com sucesso.')
        return super().form_valid(form)


class ServiceCategoryListView(SalonTenantRequiredMixin, ListView):
    model = ServiceCategory
    template_name = 'catalog/category_list.html'
    context_object_name = 'categories'
    allowed_roles = {
        UserRoleChoices.GESTOR,
        UserRoleChoices.RECEPCIONISTA,
        UserRoleChoices.PROFISSIONAL,
    }


class ServiceCategoryCreateView(GestorRequiredMixin, CreateView):
    model = ServiceCategory
    form_class = ServiceCategoryForm
    template_name = 'catalog/category_form.html'
    success_url = reverse_lazy('catalog:category_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Categoria de serviço criada com sucesso.')
        return super().form_valid(form)


class ServiceCategoryUpdateView(GestorRequiredMixin, UpdateView):
    model = ServiceCategory
    form_class = ServiceCategoryForm
    template_name = 'catalog/category_form.html'
    success_url = reverse_lazy('catalog:category_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Categoria de serviço atualizada com sucesso.')
        return super().form_valid(form)


class CommissionRuleListView(ProfissionalScopeMixin, ListView):
    model = ProfessionalServiceCommission
    template_name = 'catalog/commission_rule_list.html'
    context_object_name = 'commission_rules'
    professional_lookup_field = 'professional'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('professional', 'service', 'service__category')
        )


class CommissionRuleCreateView(GestorRequiredMixin, CreateView):
    model = ProfessionalServiceCommission
    form_class = ProfessionalServiceCommissionForm
    template_name = 'catalog/commission_rule_form.html'
    success_url = reverse_lazy('catalog:commission_rule_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            'Regra de comissão específica cadastrada com sucesso.',
        )
        return super().form_valid(form)


class CommissionRuleUpdateView(GestorRequiredMixin, UpdateView):
    model = ProfessionalServiceCommission
    form_class = ProfessionalServiceCommissionForm
    template_name = 'catalog/commission_rule_form.html'
    success_url = reverse_lazy('catalog:commission_rule_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        messages.success(
            self.request,
            'Regra de comissão específica atualizada com sucesso.',
        )
        return super().form_valid(form)


class CommissionRuleDeleteView(GestorRequiredMixin, DeleteView):
    model = ProfessionalServiceCommission
    template_name = 'catalog/commission_rule_confirm_delete.html'
    success_url = reverse_lazy('catalog:commission_rule_list')

    def form_valid(self, form):
        messages.success(self.request, 'Regra de comissão removida com sucesso.')
        return super().form_valid(form)
