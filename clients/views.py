from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from base.mixins import RecepcaoOrGestorMixin
from clients.forms import ClientForm
from clients.models import Client, normalize_digits


class ClientListView(RecepcaoOrGestorMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        if query:
            digits = normalize_digits(query)
            filters = (
                Q(full_name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone__icontains=query)
                | Q(cpf_cnpj__icontains=query)
            )
            if digits:
                filters |= Q(phone__icontains=digits) | Q(cpf_cnpj__icontains=digits)
            qs = qs.filter(filters)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '').strip()
        return context


class ClientCreateView(RecepcaoOrGestorMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('clients:client_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Cliente cadastrado com sucesso.')
        return super().form_valid(form)


class ClientUpdateView(RecepcaoOrGestorMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('clients:client_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Dados do cliente atualizados com sucesso.')
        return super().form_valid(form)


class ClientDetailView(RecepcaoOrGestorMixin, DetailView):
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointment_history'] = self.object.get_appointment_history()
        context['service_order_history'] = self.object.get_service_order_history()
        return context
