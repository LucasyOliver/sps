from django import forms
from accounts.models import User, UserRoleChoices
from scheduling.models import ProfessionalSchedule, ScheduleBlock


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
