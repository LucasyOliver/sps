from django import forms
from accounts.models import User, UserRoleChoices
from catalog.models import Service
from clients.models import Client
from scheduling.models import (
    AppointmentStatusChoices,
    ProfessionalSchedule,
    ScheduleBlock,
)


class ProfessionalScheduleForm(forms.ModelForm):
    class Meta:
        model = ProfessionalSchedule
        fields = (
            'professional',
            'weekday',
            'is_working',
            'start_time',
            'end_time',
            'break_start_time',
            'break_end_time',
        )

    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.salon = salon
        if self.salon is not None:
            self.instance.salon = self.salon
            self.fields['professional'].queryset = User.objects.filter(
                salon=self.salon,
                is_active=True,
            )


class ScheduleBlockForm(forms.ModelForm):
    class Meta:
        model = ScheduleBlock
        fields = ('professional', 'block_type', 'start_at', 'end_at', 'reason')

    def __init__(self, *args, salon=None, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.salon = salon
        self.actor = actor
        if self.salon is not None:
            self.instance.salon = self.salon
            qs = User.objects.filter(salon=self.salon, is_active=True)
            if self.actor is not None and self.actor.role == UserRoleChoices.PROFISSIONAL:
                qs = qs.filter(pk=self.actor.pk)
            self.fields['professional'].queryset = qs


class AppointmentCreateForm(forms.Form):
    client = forms.ModelChoiceField(
        label='Cliente',
        queryset=Client.objects.none(),
    )
    professional = forms.ModelChoiceField(
        label='Profissional',
        queryset=User.objects.none(),
    )
    services = forms.ModelMultipleChoiceField(
        label='Serviços',
        queryset=Service.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
    )
    start_at = forms.DateTimeField(
        label='Data e hora de início',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
    )
    notes = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, salon=None, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.salon = salon
        self.actor = actor
        if self.salon is not None:
            self.fields['client'].queryset = (
                Client.objects.for_salon(self.salon)
                .filter(is_active=True)
                .order_by('full_name')
            )
            prof_qs = User.objects.filter(
                salon=self.salon,
                is_active=True,
                role__in=[UserRoleChoices.PROFISSIONAL, UserRoleChoices.GESTOR],
            ).order_by('full_name')
            if self.actor is not None and self.actor.role == UserRoleChoices.PROFISSIONAL:
                prof_qs = prof_qs.filter(pk=self.actor.pk)
            self.fields['professional'].queryset = prof_qs
            self.fields['services'].queryset = (
                Service.objects.for_salon(self.salon)
                .filter(is_active=True)
                .order_by('name')
            )


class AppointmentRescheduleForm(forms.Form):
    professional = forms.ModelChoiceField(
        label='Profissional',
        queryset=User.objects.none(),
    )
    services = forms.ModelMultipleChoiceField(
        label='Serviços',
        queryset=Service.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
    )
    start_at = forms.DateTimeField(
        label='Nova data e hora de início',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
    )
    notes = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, salon=None, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.salon = salon
        self.actor = actor
        if self.salon is not None:
            prof_qs = User.objects.filter(
                salon=self.salon,
                is_active=True,
                role__in=[UserRoleChoices.PROFISSIONAL, UserRoleChoices.GESTOR],
            ).order_by('full_name')
            if self.actor is not None and self.actor.role == UserRoleChoices.PROFISSIONAL:
                prof_qs = prof_qs.filter(pk=self.actor.pk)
            self.fields['professional'].queryset = prof_qs
            self.fields['services'].queryset = (
                Service.objects.for_salon(self.salon)
                .filter(is_active=True)
                .order_by('name')
            )


class AppointmentStatusTransitionForm(forms.Form):
    new_status = forms.ChoiceField(
        label='Novo status',
        choices=AppointmentStatusChoices.choices,
    )
    cancellation_reason = forms.CharField(
        label='Motivo do cancelamento (obrigatório ao cancelar)',
        max_length=200,
        required=False,
    )
