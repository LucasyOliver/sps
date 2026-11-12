from django.urls import path
from accounts.views import (
    EmailLoginView,
    TeamMemberCreateView,
    TeamMemberListView,
    TeamMemberUpdateView,
    UserLogoutView,
)

app_name = 'accounts'

urlpatterns = [
    path('entrar/', EmailLoginView.as_view(), name='login'),
    path('sair/', UserLogoutView.as_view(), name='logout'),
    path('equipe/', TeamMemberListView.as_view(), name='team_list'),
    path('equipe/novo/', TeamMemberCreateView.as_view(), name='team_create'),
    path('equipe/<int:pk>/editar/', TeamMemberUpdateView.as_view(), name='team_update'),
]
