from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView
from accounts.forms import (
    EmailAuthenticationForm,
    TeamMemberCreateForm,
    TeamMemberUpdateForm,
)
from accounts.models import User
from base.mixins import GestorRequiredMixin


class EmailLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = 'accounts:login'


class TeamMemberListView(GestorRequiredMixin, ListView):
    model = User
    template_name = 'accounts/team_list.html'
    context_object_name = 'team_members'

    def get_queryset(self):
        return User.objects.filter(salon=self.request.salon).order_by('full_name')


class TeamMemberCreateView(GestorRequiredMixin, CreateView):
    model = User
    form_class = TeamMemberCreateForm
    template_name = 'accounts/team_form.html'
    success_url = reverse_lazy('accounts:team_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Membro da equipe cadastrado com sucesso.')
        return super().form_valid(form)


class TeamMemberUpdateView(GestorRequiredMixin, UpdateView):
    model = User
    form_class = TeamMemberUpdateForm
    template_name = 'accounts/team_form.html'
    success_url = reverse_lazy('accounts:team_list')

    def get_queryset(self):
        return User.objects.filter(salon=self.request.salon)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['salon'] = self.request.salon
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Dados do membro da equipe atualizados com sucesso.')
        return super().form_valid(form)
