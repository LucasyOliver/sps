from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from accounts.models import UserRoleChoices


class SalonTenantRequiredMixin(LoginRequiredMixin):
    """Garante usuário autenticado, vinculado a um salão ativo e escopa o QuerySet pelo salão."""

    allowed_roles = None

    def check_salon_and_role(self, request):
        user = request.user
        if not user.is_active or user.salon_id is None:
            raise PermissionDenied('Usuário não possui um salão ativo vinculado.')
        if not user.salon.is_active:
            raise PermissionDenied('O salão vinculado a este usuário está inativo.')
        if self.allowed_roles is not None and user.role not in self.allowed_roles:
            raise PermissionDenied('Perfil de usuário sem permissão para esta operação.')
        request.salon = user.salon

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.check_salon_and_role(request)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(queryset, 'for_salon'):
            return queryset.for_salon(self.request.salon)
        return queryset.filter(salon=self.request.salon)


class GestorRequiredMixin(SalonTenantRequiredMixin):
    """Restringe o acesso exclusivamente ao Proprietário / Gestor do próprio salão."""

    allowed_roles = {UserRoleChoices.GESTOR}


class RecepcaoOrGestorMixin(SalonTenantRequiredMixin):
    """Permite acesso ao Gestor e à Recepcionista do próprio salão."""

    allowed_roles = {
        UserRoleChoices.GESTOR,
        UserRoleChoices.RECEPCIONISTA,
    }


class ProfissionalScopeMixin(SalonTenantRequiredMixin):
    """Permite acesso à equipe do salão e restringe o escopo ao próprio profissional quando aplicável."""

    allowed_roles = {
        UserRoleChoices.GESTOR,
        UserRoleChoices.RECEPCIONISTA,
        UserRoleChoices.PROFISSIONAL,
    }
    professional_lookup_field = 'professional'

    def get_queryset(self):
        queryset = super().get_queryset()
        if (
            self.request.user.role == UserRoleChoices.PROFISSIONAL
            and self.professional_lookup_field
        ):
            return queryset.filter(**{self.professional_lookup_field: self.request.user})
        return queryset
