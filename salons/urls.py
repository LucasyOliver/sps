from django.urls import path
from salons.views import (
    SalonBusinessHoursListView,
    SalonBusinessHoursUpsertView,
    SalonHolidayCreateView,
    SalonHolidayDeleteView,
    SalonHolidayListView,
    SalonSettingsUpdateView,
)

app_name = 'salons'

urlpatterns = [
    path('configuracoes/', SalonSettingsUpdateView.as_view(), name='settings'),
    path('<int:pk>/editar/', SalonSettingsUpdateView.as_view(), name='settings_by_pk'),
    path('expediente/', SalonBusinessHoursListView.as_view(), name='business_hours'),
    path('expediente/salvar/', SalonBusinessHoursUpsertView.as_view(), name='business_hours_save'),
    path('feriados/', SalonHolidayListView.as_view(), name='holidays'),
    path('feriados/novo/', SalonHolidayCreateView.as_view(), name='holiday_create'),
    path('feriados/<int:pk>/excluir/', SalonHolidayDeleteView.as_view(), name='holiday_delete'),
]
