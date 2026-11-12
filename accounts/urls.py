from django.urls import path
from accounts.views import EmailLoginView, UserLogoutView

app_name = 'accounts'

urlpatterns = [
    path('entrar/', EmailLoginView.as_view(), name='login'),
    path('sair/', UserLogoutView.as_view(), name='logout'),
]
