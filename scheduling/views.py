from datetime import date, timedelta
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView
from accounts.models import User, UserRoleChoices
from base.mixins import GestorRequiredMixin, ProfissionalScopeMixin
from scheduling.forms import (
    AppointmentCreateForm,
    AppointmentRescheduleForm,
    AppointmentStatusTransitionForm,
    ProfessionalScheduleForm,
    ScheduleBlockForm,
)
from scheduling.models import Appointment, ProfessionalSchedule, ScheduleBlock
from scheduling.services import AvailabilityService, SchedulingService


def _attach_validation_error_to_form(form, exc: ValidationError):
    if hasattr(exc, 'message_dict'):
        for field_name, messages_list in exc.message_dict.items():
            target_field = field_name if field_name in form.fields else None
            for msg in messages_list:
                form.add_error(target_field, msg)
    else:
        for msg in exc.messages:
            form.add_error(None, msg)


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


class AppointmentAgendaListView(ProfissionalScopeMixin, ListView):
    model = Appointment
    template_name = 'scheduling/appointment_list.html'
    context_object_name = 'appointments'
    professional_lookup_field = 'professional'

    def _parse_reference_date(self) -> date:
        date_str = self.request.GET.get('date', '').strip()
        if date_str:
            try:
                return date.fromisoformat(date_str)
            except ValueError:
                pass
        return timezone.localdate()

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related('client', 'professional')
            .prefetch_related('items__service')
        )
        view_mode = self.request.GET.get('view', 'day').strip()
        date_str = self.request.GET.get('date', '').strip()
        prof_id = self.request.GET.get('professional', '').strip()
        status_filter = self.request.GET.get('status', '').strip()

        if date_str:
            ref_date = self._parse_reference_date()
            if view_mode == 'week':
                week_start = ref_date - timedelta(days=ref_date.weekday())
                week_end = week_start + timedelta(days=6)
                qs = qs.filter(
                    start_at__date__gte=week_start,
                    start_at__date__lte=week_end,
                )
            else:
                qs = qs.filter(start_at__date=ref_date)

        if (
            prof_id.isdigit()
            and self.request.user.role != UserRoleChoices.PROFISSIONAL
        ):
            qs = qs.filter(professional_id=int(prof_id))

        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs.order_by('start_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ref_date = self._parse_reference_date()
        prof_qs = User.objects.filter(
            salon=self.request.salon,
            is_active=True,
            role__in=[UserRoleChoices.PROFISSIONAL, UserRoleChoices.GESTOR],
        ).order_by('full_name')
        if self.request.user.role == UserRoleChoices.PROFISSIONAL:
            prof_qs = prof_qs.filter(pk=self.request.user.pk)

        context['professionals'] = prof_qs
        context['reference_date'] = ref_date
        context['view_mode'] = self.request.GET.get('view', 'day').strip()
        context['selected_professional'] = self.request.GET.get('professional', '').strip()
        context['selected_status'] = self.request.GET.get('status', '').strip()

        selected_prof_obj = None
        if self.request.user.role == UserRoleChoices.PROFISSIONAL:
            selected_prof_obj = self.request.user
        elif context['selected_professional'].isdigit():
            selected_prof_obj = prof_qs.filter(
                pk=int(context['selected_professional'])
            ).first()

        if selected_prof_obj is not None:
            context['available_slots'] = AvailabilityService.get_available_slots(
                salon=self.request.salon,
                professional=selected_prof_obj,
                target_date=ref_date,
                duration_minutes=30,
            )
        else:
            context['available_slots'] = []

        return context


class AppointmentCreateView(ProfissionalScopeMixin, FormView):
    form_class = AppointmentCreateForm
    template_name = 'scheduling/appointment_form.html'
    success_url = reverse_lazy('scheduling:appointment_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        kwargs['actor'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            SchedulingService.create_appointment(
                salon=self.request.salon,
                client=form.cleaned_data['client'],
                professional=form.cleaned_data['professional'],
                start_at=form.cleaned_data['start_at'],
                services=form.cleaned_data['services'],
                notes=form.cleaned_data.get('notes', ''),
                created_by=self.request.user,
            )
        except ValidationError as exc:
            _attach_validation_error_to_form(form, exc)
            return self.form_invalid(form)

        messages.success(self.request, 'Agendamento criado com sucesso.')
        return redirect(self.get_success_url())


class AppointmentDetailView(ProfissionalScopeMixin, DetailView):
    model = Appointment
    template_name = 'scheduling/appointment_detail.html'
    context_object_name = 'appointment'
    professional_lookup_field = 'professional'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('client', 'professional', 'created_by')
            .prefetch_related('items__service')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_form'] = AppointmentStatusTransitionForm(
            initial={'new_status': self.object.status}
        )
        return context


class AppointmentRescheduleView(ProfissionalScopeMixin, FormView):
    form_class = AppointmentRescheduleForm
    template_name = 'scheduling/appointment_reschedule.html'
    professional_lookup_field = 'professional'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.check_salon_and_role(request)
        qs = Appointment.objects.for_salon(request.salon).select_related(
            'client', 'professional'
        )
        if request.user.role == UserRoleChoices.PROFISSIONAL:
            qs = qs.filter(professional=request.user)
        self.appointment = get_object_or_404(qs, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {
            'professional': self.appointment.professional_id,
            'services': list(
                self.appointment.items.values_list('service_id', flat=True)
            ),
            'start_at': timezone.localtime(self.appointment.start_at).strftime(
                '%Y-%m-%dT%H:%M'
            ),
            'notes': self.appointment.notes,
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        kwargs['actor'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointment'] = self.appointment
        return context

    def form_valid(self, form):
        try:
            SchedulingService.reschedule_appointment(
                appointment=self.appointment,
                new_start_at=form.cleaned_data['start_at'],
                new_professional=form.cleaned_data['professional'],
                new_services=form.cleaned_data['services'],
                notes=form.cleaned_data.get('notes', ''),
            )
        except ValidationError as exc:
            _attach_validation_error_to_form(form, exc)
            return self.form_invalid(form)

        messages.success(self.request, 'Agendamento remarcado com sucesso.')
        return redirect(
            reverse('scheduling:appointment_detail', args=[self.appointment.pk])
        )


class AppointmentStatusTransitionView(ProfissionalScopeMixin, FormView):
    form_class = AppointmentStatusTransitionForm
    template_name = 'scheduling/appointment_detail.html'
    professional_lookup_field = 'professional'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.check_salon_and_role(request)
        qs = Appointment.objects.for_salon(request.salon).select_related(
            'client', 'professional'
        )
        if request.user.role == UserRoleChoices.PROFISSIONAL:
            qs = qs.filter(professional=request.user)
        self.appointment = get_object_or_404(qs, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointment'] = self.appointment
        context['status_form'] = context.get('form')
        return context

    def form_valid(self, form):
        try:
            SchedulingService.transition_status(
                appointment=self.appointment,
                new_status=form.cleaned_data['new_status'],
                cancellation_reason=form.cleaned_data.get('cancellation_reason', ''),
            )
        except ValidationError as exc:
            _attach_validation_error_to_form(form, exc)
            return self.form_invalid(form)

        messages.success(self.request, 'Status do agendamento atualizado com sucesso.')
        return redirect(
            reverse('scheduling:appointment_detail', args=[self.appointment.pk])
        )
