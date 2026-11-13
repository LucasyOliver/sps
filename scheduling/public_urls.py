from django.urls import path
from scheduling.views import (
    PublicAppointmentDetailCancelView,
    PublicSalonBookingView,
)

app_name = 'public_booking'

urlpatterns = [
    path('', PublicSalonBookingView.as_view(), name='salon_booking'),
    path(
        'agendamento/<uuid:public_token>/',
        PublicAppointmentDetailCancelView.as_view(),
        name='appointment_detail',
    ),
]
