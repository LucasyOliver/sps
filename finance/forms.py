from decimal import Decimal
from django import forms
from finance.models import CashTransactionTypeChoices, PaymentMethodChoices

MONEY_KWARGS = {'max_digits': 10, 'decimal_places': 2, 'min_value': Decimal('0.00')}
POSITIVE_MONEY_KWARGS = {'max_digits': 10, 'decimal_places': 2, 'min_value': Decimal('0.01')}


class CashSessionOpenForm(forms.Form):
    opening_balance = forms.DecimalField(
        label='Saldo inicial em caixa (R$)',
        initial=Decimal('0.00'),
        **MONEY_KWARGS,
    )
    notes = forms.CharField(
        label='Observações de abertura (opcional)',
        required=False,
        max_length=200,
    )


class CashSessionCloseForm(forms.Form):
    closing_balance_counted = forms.DecimalField(
        label='Saldo final conferido na gaveta/conta (R$)',
        **MONEY_KWARGS,
    )
    notes = forms.CharField(
        label='Observações de fechamento (opcional)',
        required=False,
        max_length=200,
    )


class ManualCashTransactionForm(forms.Form):
    transaction_type = forms.ChoiceField(
        label='Tipo de lançamento',
        choices=[
            (CashTransactionTypeChoices.MANUAL_INCOME, 'Entrada avulsa / Suprimento'),
            (CashTransactionTypeChoices.MANUAL_EXPENSE, 'Saída / Despesa do salão'),
        ],
    )
    payment_method = forms.ChoiceField(
        label='Meio de movimentação',
        choices=PaymentMethodChoices.choices,
        initial=PaymentMethodChoices.CASH,
    )
    amount = forms.DecimalField(label='Valor (R$)', **POSITIVE_MONEY_KWARGS)
    description = forms.CharField(label='Descrição / Motivo', max_length=200)


class OrderCheckoutForm(forms.Form):
    payment_method_1 = forms.ChoiceField(
        label='Meio de pagamento (1ª parcela ou integral)',
        choices=PaymentMethodChoices.choices,
        initial=PaymentMethodChoices.PIX,
    )
    amount_1 = forms.DecimalField(
        label='Valor 1 (R$)',
        **POSITIVE_MONEY_KWARGS,
    )
    payment_method_2 = forms.ChoiceField(
        label='2º Meio de pagamento (opcional — pagamento misto)',
        choices=[('', '— Sem 2ª parcela —'), *PaymentMethodChoices.choices],
        required=False,
    )
    amount_2 = forms.DecimalField(
        label='Valor 2 (R$ — opcional)',
        required=False,
        **POSITIVE_MONEY_KWARGS,
    )

    def to_payments_list(self) -> list[dict]:
        payments = [
            {
                'payment_method': self.cleaned_data['payment_method_1'],
                'amount': self.cleaned_data['amount_1'],
            }
        ]
        method_2 = self.cleaned_data.get('payment_method_2')
        amount_2 = self.cleaned_data.get('amount_2')
        if method_2 and amount_2:
            payments.append({'payment_method': method_2, 'amount': amount_2})
        return payments


class OrderReversalForm(forms.Form):
    reason = forms.CharField(
        label='Motivo do estorno (obrigatório para auditoria)',
        max_length=200,
    )
