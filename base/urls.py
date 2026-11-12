from django.urls import path
from base.views import HomeView, LivenessCheckView, ReadinessCheckView

app_name = 'base'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('healthz/', LivenessCheckView.as_view(), name='healthz'),
    path('readyz/', ReadinessCheckView.as_view(), name='readyz'),
]
