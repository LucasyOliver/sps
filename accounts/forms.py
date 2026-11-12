from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm
from accounts.models import User, UserRoleChoices

SALON_INTERNAL_ROLE_CHOICES = [
    (UserRoleChoices.GESTOR, UserRoleChoices.GESTOR.label),
    (UserRoleChoices.RECEPCIONISTA, UserRoleChoices.RECEPCIONISTA.label),
    (UserRoleChoices.PROFISSIONAL, UserRoleChoices.PROFISSIONAL.label),
]


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


class TeamMemberCreateForm(UserCreationForm):
    role = forms.ChoiceField(
        label='Perfil no salão',
        choices=SALON_INTERNAL_ROLE_CHOICES,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'full_name', 'phone', 'role', 'tax_document', 'is_active')

    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.salon = salon
        if self.salon is not None:
            self.instance.salon = self.salon

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.salon is not None:
            user.salon = self.salon
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.full_clean()
            user.save()
        return user


class TeamMemberUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(
        label='Perfil no salão',
        choices=SALON_INTERNAL_ROLE_CHOICES,
    )

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone', 'role', 'tax_document', 'is_active')

    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.salon = salon
        if self.salon is not None:
            self.instance.salon = self.salon

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.salon is not None:
            user.salon = self.salon
        if commit:
            user.full_clean()
            user.save()
        return user
