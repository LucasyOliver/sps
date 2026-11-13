from django import forms
from django.core.exceptions import ValidationError
from inventory.models import Product, StockMovementTypeChoices
from inventory.services import MANUAL_MOVEMENT_TYPES


class ProductForm(forms.ModelForm):
    initial_stock = forms.IntegerField(
        label='Saldo inicial (opcional)',
        min_value=0,
        required=False,
        help_text='Gera automaticamente uma movimentação auditada de "Entrada por compra".',
    )

    class Meta:
        model = Product
        fields = [
            'name',
            'sku',
            'usage_type',
            'unit',
            'cost_price',
            'sale_price',
            'min_stock_alert',
            'is_active',
            'ncm_code',
            'cest_code',
            'cfop_default',
            'tax_origin',
            'icms_rate_pct',
            'pis_cofins_regime',
        ]

    def __init__(self, *args, salon=None, **kwargs):
        self.salon = salon
        super().__init__(*args, **kwargs)
        if self.salon is not None:
            self.instance.salon = self.salon
        if self.instance.pk:
            # Após o cadastro, o saldo só muda via movimentações auditadas (RF-008).
            self.fields.pop('initial_stock')

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if self.salon is not None:
            qs = Product.objects.for_salon(self.salon).filter(name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Já existe um produto com este nome neste salão.')
        return name

    def clean_sku(self):
        sku = (self.cleaned_data.get('sku') or '').strip()
        if sku and self.salon is not None:
            qs = Product.objects.for_salon(self.salon).filter(sku=sku)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Já existe um produto com este SKU neste salão.')
        return sku


class StockMovementForm(forms.Form):
    product = forms.ModelChoiceField(label='Produto', queryset=Product.objects.none())
    movement_type = forms.ChoiceField(
        label='Tipo de movimentação',
        choices=[
            (value, label)
            for value, label in StockMovementTypeChoices.choices
            if value in MANUAL_MOVEMENT_TYPES
        ],
    )
    quantity = forms.IntegerField(
        label='Quantidade',
        help_text='Para ajuste de inventário, use valor negativo para reduzir o saldo (ex.: -2).',
    )
    reason = forms.CharField(
        label='Motivo / Observação',
        max_length=200,
        required=False,
        help_text='Obrigatório para ajustes de inventário.',
    )

    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.salon = salon
        if self.salon is not None:
            self.fields['product'].queryset = (
                Product.objects.for_salon(self.salon).filter(is_active=True).order_by('name')
            )
