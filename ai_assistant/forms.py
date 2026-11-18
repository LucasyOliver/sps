from django import forms


class AssistantPromptForm(forms.Form):
    prompt = forms.CharField(
        label='Pergunte ao Assistente Gerencial do Salão',
        max_length=600,
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'placeholder': (
                    'Ex.: Qual o faturamento e quanto tenho de comissão pendente? '
                    'Quais produtos estão com estoque baixo? Quais clientes estão inativos?'
                ),
            }
        ),
    )
