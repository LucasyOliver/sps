from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm
from accounts.models import User


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(
            attrs={
                'autofocus': True,
                'placeholder': 'seu@email.com.br',
                'autocomplete': 'email',
            }
        ),
    )
    password = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'placeholder': '••••••••',
                'autocomplete': 'current-password',
            }
        ),
    )


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'full_name', 'role', 'salon', 'phone', 'tax_document', 'is_active', 'is_staff')


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('email', 'full_name', 'role', 'salon', 'phone', 'tax_document', 'is_active', 'is_staff')
