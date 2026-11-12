from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, FormView, ListView
from base.mixins import GestorRequiredMixin, ProfissionalScopeMixin
from scheduling.forms import ProfessionalScheduleForm, ScheduleBlockForm
from scheduling.models import ProfessionalSchedule, ScheduleBlock


class ProfessionalScheduleListView(ProfissionalScopeMixin, ListView):
    model = ProfessionalSchedule
    template_name = 'scheduling/professional_schedule_list.html'
    context_object_name = 'schedules'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ProfessionalScheduleForm(salon=self.request.salon)
        return context


class ProfessionalScheduleUpsertView(GestorRequiredMixin, FormView):
    form_class = ProfessionalScheduleForm
    template_name = 'scheduling/professional_schedule_list.html'
    success_url = reverse_lazy('scheduling:professional_schedules')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        professional_id = self.request.POST.get('professional')
        weekday = self.request.POST.get('weekday')
        if (
            professional_id
            and str(professional_id).isdigit()
            and weekday is not None
            and str(weekday).isdigit()
        ):
            existing = ProfessionalSchedule.objects.for_salon(self.request.salon).filter(
                professional_id=int(professional_id),
                weekday=int(weekday),
            ).first()
            if existing is not None:
                kwargs['instance'] = existing
        return kwargs

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.salon = self.request.salon
        instance.full_clean()
        instance.save()
        messages.success(self.request, 'Expediente individual do profissional salvo com sucesso.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schedules'] = ProfessionalSchedule.objects.for_salon(self.request.salon)
        return context


class ScheduleBlockListView(ProfissionalScopeMixin, ListView):
    model = ScheduleBlock
    template_name = 'scheduling/schedule_block_list.html'
    context_object_name = 'blocks'


class ScheduleBlockCreateView(ProfissionalScopeMixin, CreateView):
    model = ScheduleBlock
    form_class = ScheduleBlockForm
    template_name = 'scheduling/schedule_block_form.html'
    success_url = reverse_lazy('scheduling:schedule_blocks')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        kwargs['actor'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.salon = self.request.salon
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Bloqueio de agenda registrado com sucesso.')
        return super().form_valid(form)


class ScheduleBlockDeleteView(ProfissionalScopeMixin, DeleteView):
    model = ScheduleBlock
    template_name = 'scheduling/schedule_block_confirm_delete.html'
    success_url = reverse_lazy('scheduling:schedule_blocks')
