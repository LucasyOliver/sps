from django.urls import path
from scheduling.views import (
    AppointmentAgendaListView,
    AppointmentCreateView,
    AppointmentDetailView,
    AppointmentRescheduleView,
    AppointmentStatusTransitionView,
    ProfessionalScheduleListView,
    ProfessionalScheduleUpsertView,
    ScheduleBlockCreateView,
    ScheduleBlockDeleteView,
    ScheduleBlockListView,
)

app_name = 'scheduling'

urlpatterns = [
    path('', AppointmentAgendaListView.as_view(), name='appointment_list'),
    path('novo/', AppointmentCreateView.as_view(), name='appointment_create'),
    path('<int:pk>/', AppointmentDetailView.as_view(), name='appointment_detail'),
    path('<int:pk>/remarcar/', AppointmentRescheduleView.as_view(), name='appointment_reschedule'),
    path('<int:pk>/status/', AppointmentStatusTransitionView.as_view(), name='appointment_status'),
    path('expedientes/', ProfessionalScheduleListView.as_view(), name='professional_schedules'),
    path('expedientes/salvar/', ProfessionalScheduleUpsertView.as_view(), name='professional_schedule_save'),
    path('bloqueios/', ScheduleBlockListView.as_view(), name='schedule_blocks'),
    path('bloqueios/novo/', ScheduleBlockCreateView.as_view(), name='schedule_block_create'),
    path('bloqueios/<int:pk>/excluir/', ScheduleBlockDeleteView.as_view(), name='schedule_block_delete'),
]
