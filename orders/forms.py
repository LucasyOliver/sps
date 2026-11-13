from decimal import Decimal
from django import forms
from accounts.models import User, UserRoleChoices
from catalog.models import Service
from clients.models import Client
from inventory.models import SALE_USAGE_TYPES, Product

MONEY_FIELD_KWARGS = {'max_digits': 10, 'decimal_places': 2, 'min_value': Decimal('0.00')}


class ServiceOrderCreateForm(forms.Form):
    client = forms.ModelChoiceField(
        label='Cliente',
        queryset=Client.objects.none(),
        required=False,
        help_text='Deixe em branco apenas para venda avulsa de balcão sem identificação.',
    )
    notes = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )

    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        if salon is not None:
            self.fields['client'].queryset = (
                Client.objects.for_salon(salon).filter(is_active=True).order_by('full_name')
            )


class OrderServiceItemForm(forms.Form):
    service = forms.ModelChoiceField(label='Serviço executado', queryset=Service.objects.none())
    professional = forms.ModelChoiceField(label='Profissional executante', queryset=User.objects.none())
    gross_price = forms.DecimalField(
        label='Valor bruto (R$)',
        required=False,
        help_text='Em branco utiliza o preço base do serviço.',
        **MONEY_FIELD_KWARGS,
    )
    discount_amount = forms.DecimalField(
        label='Desconto do item (R$)',
        required=False,
        initial=Decimal('0.00'),
        **MONEY_FIELD_KWARGS,
    )

    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        if salon is not None:
            self.fields['service'].queryset = (
                Service.objects.for_salon(salon).filter(is_active=True).order_by('name')
            )
            self.fields['professional'].queryset = User.objects.filter(
                salon=salon,
                is_active=True,
                role__in=[UserRoleChoices.PROFISSIONAL, UserRoleChoices.GESTOR],
            ).order_by('full_name')


class OrderProductItemForm(forms.Form):
    product = forms.ModelChoiceField(label='Produto vendido', queryset=Product.objects.none())
    quantity = forms.IntegerField(label='Quantidade', min_value=1, initial=1)
    unit_price = forms.DecimalField(
        label='Valor unitário (R$)',
        required=False,
        help_text='Em branco utiliza o preço de venda cadastrado.',
        **MONEY_FIELD_KWARGS,
    )

    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        if salon is not None:
            self.fields['product'].queryset = (
                Product.objects.for_salon(salon)
                .filter(is_active=True, usage_type__in=SALE_USAGE_TYPES)
                .order_by('name')
            )


class OrderAdjustmentForm(forms.Form):
    discount_amount = forms.DecimalField(label='Desconto geral (R$)', **MONEY_FIELD_KWARGS)
    surcharge_amount = forms.DecimalField(label='Acréscimo (R$)', **MONEY_FIELD_KWARGS)


class OrderCancelForm(forms.Form):
    cancellation_reason = forms.CharField(label='Motivo do cancelamento', max_length=200)
