from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, FormView, ListView, UpdateView
from base.mixins import GestorRequiredMixin, SalonTenantRequiredMixin
from salons.forms import SalonBusinessHoursForm, SalonHolidayForm, SalonSettingsForm
from salons.models import Salon, SalonBusinessHours, SalonHoliday


class SalonSettingsUpdateView(GestorRequiredMixin, UpdateView):
    model = Salon
    form_class = SalonSettingsForm
    template_name = 'salons/salon_settings_form.html'
    success_url = reverse_lazy('salons:settings')

    def get_queryset(self):
        return Salon.objects.filter(pk=self.request.salon.pk)

    def get_object(self, queryset=None):
        if 'pk' in self.kwargs:
            return super().get_object(queryset)
        return self.request.salon

    def form_valid(self, form):
        messages.success(self.request, 'Configurações e dados fiscais do salão atualizados com sucesso.')
        return super().form_valid(form)


class SalonBusinessHoursListView(SalonTenantRequiredMixin, ListView):
    model = SalonBusinessHours
    template_name = 'salons/business_hours_list.html'
    context_object_name = 'business_hours_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SalonBusinessHoursForm(salon=self.request.salon)
        return context


class SalonBusinessHoursUpsertView(GestorRequiredMixin, FormView):
    form_class = SalonBusinessHoursForm
    template_name = 'salons/business_hours_list.html'
    success_url = reverse_lazy('salons:business_hours')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        weekday = self.request.POST.get('weekday')
        if weekday is not None and str(weekday).isdigit():
            existing = SalonBusinessHours.objects.for_salon(self.request.salon).filter(
                weekday=int(weekday)
            ).first()
            if existing is not None:
                kwargs['instance'] = existing
        return kwargs

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.salon = self.request.salon
        instance.full_clean()
        instance.save()
        messages.success(self.request, 'Horário de funcionamento do salão salvo com sucesso.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business_hours_list'] = SalonBusinessHours.objects.for_salon(self.request.salon)
        return context


class SalonHolidayListView(SalonTenantRequiredMixin, ListView):
    model = SalonHoliday
    template_name = 'salons/holiday_list.html'
    context_object_name = 'holidays'


class SalonHolidayCreateView(GestorRequiredMixin, CreateView):
    model = SalonHoliday
    form_class = SalonHolidayForm
    template_name = 'salons/holiday_form.html'
    success_url = reverse_lazy('salons:holidays')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        form.instance.salon = self.request.salon
        messages.success(self.request, 'Feriado ou fechamento especial registrado com sucesso.')
        return super().form_valid(form)


class SalonHolidayDeleteView(GestorRequiredMixin, DeleteView):
    model = SalonHoliday
    template_name = 'salons/holiday_confirm_delete.html'
    success_url = reverse_lazy('salons:holidays')
