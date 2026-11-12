from django import forms
from django.core.exceptions import ValidationError
from accounts.models import User, UserRoleChoices
from catalog.models import ProfessionalServiceCommission, Service, ServiceCategory


class ServiceCategoryForm(forms.ModelForm):
    class Meta:
        model = ServiceCategory
        fields = ['name', 'description', 'is_active']

    def __init__(self, *args, salon=None, **kwargs):
        self.salon = salon
        super().__init__(*args, **kwargs)
        if self.salon is not None:
            self.instance.salon = self.salon

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if self.salon is not None:
            qs = ServiceCategory.objects.for_salon(self.salon).filter(name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Já existe uma categoria com este nome neste salão.')
        return name


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            'category',
            'name',
            'description',
            'duration_minutes',
            'base_price',
            'default_commission_pct',
            'professionals',
            'lc116_service_code',
            'cnae_code',
            'iss_rate_pct',
            'is_active',
        ]
        widgets = {
            'professionals': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, salon=None, **kwargs):
        self.salon = salon
        super().__init__(*args, **kwargs)
        if self.salon is not None:
            self.instance.salon = self.salon
            self.fields['category'].queryset = ServiceCategory.objects.for_salon(
                self.salon
            ).filter(is_active=True)
            self.fields['professionals'].queryset = User.objects.filter(
                salon=self.salon,
                is_active=True,
                role__in=[UserRoleChoices.PROFISSIONAL, UserRoleChoices.GESTOR],
            ).order_by('full_name')

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if self.salon is not None:
            qs = Service.objects.for_salon(self.salon).filter(name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Já existe um serviço com este nome neste salão.')
        return name

    def clean_professionals(self):
        professionals = self.cleaned_data.get('professionals')
        if professionals and self.salon is not None:
            for prof in professionals:
                if prof.salon_id != self.salon.id:
                    raise ValidationError(
                        'Todos os profissionais selecionados devem pertencer a este salão.'
                    )
        return professionals


class ProfessionalServiceCommissionForm(forms.ModelForm):
    class Meta:
        model = ProfessionalServiceCommission
        fields = [
            'professional',
            'service',
            'commission_pct',
            'is_active',
        ]

    def __init__(self, *args, salon=None, **kwargs):
        self.salon = salon
        super().__init__(*args, **kwargs)
        if self.salon is not None:
            self.instance.salon = self.salon
            self.fields['professional'].queryset = User.objects.filter(
                salon=self.salon,
                is_active=True,
                role__in=[UserRoleChoices.PROFISSIONAL, UserRoleChoices.GESTOR],
            ).order_by('full_name')
            self.fields['service'].queryset = Service.objects.for_salon(
                self.salon
            ).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        professional = cleaned_data.get('professional')
        service = cleaned_data.get('service')
        if self.salon is not None and professional and service:
            qs = ProfessionalServiceCommission.objects.for_salon(self.salon).filter(
                professional=professional,
                service=service,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    'Já existe uma regra de comissão cadastrada para este profissional e serviço.'
                )
        return cleaned_data
