from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.forms import CustomUserChangeForm, CustomUserCreationForm
from accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = (
        'email',
        'full_name',
        'role',
        'salon',
        'is_active',
        'is_staff',
        'created_at',
    )
    list_filter = ('role', 'is_active', 'is_staff', 'salon')
    search_fields = ('email', 'full_name', 'phone', 'tax_document')
    ordering = ('email',)
    readonly_fields = ('created_at', 'updated_at', 'last_login')

    fieldsets = (
        ('Credenciais de Acesso', {'fields': ('email', 'password')}),
        (
            'Identificação e Vínculo Multi-tenant',
            {'fields': ('full_name', 'phone', 'role', 'salon', 'tax_document')},
        ),
        (
            'Permissões e Status',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        ('Datas de Auditoria', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'full_name',
                    'role',
                    'salon',
                    'phone',
                    'tax_document',
                    'password1',
                    'password2',
                    'is_active',
                    'is_staff',
                ),
            },
        ),
    )
