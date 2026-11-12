from django import forms
from salons.models import Salon, SalonBusinessHours, SalonHoliday


class SalonSettingsForm(forms.ModelForm):
    class Meta:
        model = Salon
        fields = (
            'trade_name',
            'name',
            'phone',
            'email',
            'cancellation_min_hours',
            'cnpj',
            'municipal_registration',
            'state_registration',
            'tax_regime',
            'is_partner_salon_regime',
            'ibge_city_code',
            'address_street',
            'address_number',
            'address_complement',
            'address_neighborhood',
            'address_city',
            'address_state',
            'address_zip_code',
        )


class SalonBusinessHoursForm(forms.ModelForm):
    class Meta:
        model = SalonBusinessHours
        fields = ('weekday', 'is_open', 'opening_time', 'closing_time')

    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.salon = salon
        if self.salon is not None:
            self.instance.salon = self.salon


class SalonHolidayForm(forms.ModelForm):
    class Meta:
        model = SalonHoliday
        fields = ('date', 'description', 'is_closed_all_day', 'opening_time', 'closing_time')

    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.salon = salon
        if self.salon is not None:
            self.instance.salon = self.salon
