from django.urls import path
from scheduling.views import (
    ProfessionalScheduleListView,
    ProfessionalScheduleUpsertView,
    ScheduleBlockCreateView,
    ScheduleBlockDeleteView,
    ScheduleBlockListView,
)

app_name = 'scheduling'

urlpatterns = [
    path('expedientes/', ProfessionalScheduleListView.as_view(), name='professional_schedules'),
    path('expedientes/salvar/', ProfessionalScheduleUpsertView.as_view(), name='professional_schedule_save'),
    path('bloqueios/', ScheduleBlockListView.as_view(), name='schedule_blocks'),
    path('bloqueios/novo/', ScheduleBlockCreateView.as_view(), name='schedule_block_create'),
    path('bloqueios/<int:pk>/excluir/', ScheduleBlockDeleteView.as_view(), name='schedule_block_delete'),
]
