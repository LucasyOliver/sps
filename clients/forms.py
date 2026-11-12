from django import forms
from clients.models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'full_name',
            'phone',
            'email',
            'birth_date',
            'notes',
            'cpf_cnpj',
            'address_street',
            'address_number',
            'address_complement',
            'address_neighborhood',
            'address_city',
            'address_state',
            'address_zip_code',
            'ibge_city_code',
            'is_active',
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, salon=None, **kwargs):
        self.salon = salon
        super().__init__(*args, **kwargs)
        if self.salon is not None:
            self.instance.salon = self.salon
