from datetime import timedelta
from decimal import Decimal
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from base.models import TenantScopedModel
from salons.models import SalonBusinessHours, WeekdayChoices


class ScheduleBlockTypeChoices(models.TextChoices):
    VACATION = 'ferias', 'Férias'
    DAY_OFF = 'folga', 'Folga'
    ABSENCE = 'ausencia', 'Ausência / Compromisso'
    OTHER = 'outro', 'Outro bloqueio'


class AppointmentStatusChoices(models.TextChoices):
    SCHEDULED = 'agendado', 'Agendado'
    CONFIRMED = 'confirmado', 'Confirmado'
    IN_PROGRESS = 'em_atendimento', 'Em atendimento'
    COMPLETED = 'concluido', 'Concluído'
    CANCELLED = 'cancelado', 'Cancelado'
    NO_SHOW = 'nao_compareceu', 'Não compareceu'


ACTIVE_APPOINTMENT_STATUSES = (
    AppointmentStatusChoices.SCHEDULED,
    AppointmentStatusChoices.CONFIRMED,
    AppointmentStatusChoices.IN_PROGRESS,
)


class ProfessionalSchedule(TenantScopedModel):
    professional = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='work_schedules',
        verbose_name='Profissional',
    )
    weekday = models.PositiveSmallIntegerField(
        'Dia da semana',
        choices=WeekdayChoices.choices,
    )
    is_working = models.BooleanField('Atende neste dia', default=True)
    start_time = models.TimeField('Início do expediente', null=True, blank=True)
    end_time = models.TimeField('Fim do expediente', null=True, blank=True)
    break_start_time = models.TimeField('Início do intervalo', null=True, blank=True)
    break_end_time = models.TimeField('Fim do intervalo', null=True, blank=True)

    class Meta:
        verbose_name = 'Expediente individual do profissional'
        verbose_name_plural = 'Expedientes individuais dos profissionais'
        ordering = ['professional', 'weekday']
        constraints = [
            models.UniqueConstraint(
                fields=['salon', 'professional', 'weekday'],
                name='unique_professional_weekday_schedule',
            )
        ]

    def __str__(self):
        day_label = self.get_weekday_display()
        if not self.is_working:
            return f'{self.professional.full_name} - {day_label}: Folga'
        return f'{self.professional.full_name} - {day_label}: {self.start_time} às {self.end_time}'

    def clean(self):
        super().clean()
        if self.professional_id and self.salon_id:
            if self.professional.salon_id != self.salon_id:
                raise ValidationError(
                    {'professional': 'O profissional selecionado não pertence a este salão.'}
                )

        if not self.is_working:
            self.start_time = None
            self.end_time = None
            self.break_start_time = None
            self.break_end_time = None
            return

        if not self.start_time or not self.end_time:
            raise ValidationError(
                'Informe os horários de início e fim do expediente quando o profissional atende no dia.'
            )
        if self.start_time >= self.end_time:
            raise ValidationError(
                {'end_time': 'O fim do expediente deve ser posterior ao início do expediente.'}
            )

        if self.break_start_time or self.break_end_time:
            if not self.break_start_time or not self.break_end_time:
                raise ValidationError(
                    'Informe tanto o início quanto o fim do intervalo de descanso.'
                )
            if self.break_start_time >= self.break_end_time:
                raise ValidationError(
                    {'break_end_time': 'O fim do intervalo deve ser posterior ao início do intervalo.'}
                )
            if self.break_start_time < self.start_time or self.break_end_time > self.end_time:
                raise ValidationError(
                    'O intervalo de descanso deve estar contido dentro do expediente do profissional.'
                )

        if self.salon_id is not None and self.weekday is not None:
            salon_hours = SalonBusinessHours.objects.filter(
                salon_id=self.salon_id,
                weekday=self.weekday,
            ).first()
            if salon_hours is not None:
                if not salon_hours.is_open:
                    raise ValidationError(
                        'O profissional não pode ter expediente ativo em um dia em que o salão está fechado.'
                    )
                if (
                    self.start_time < salon_hours.opening_time
                    or self.end_time > salon_hours.closing_time
                ):
                    raise ValidationError(
                        'O expediente do profissional deve estar contido no horário de funcionamento do salão.'
                    )


class ScheduleBlock(TenantScopedModel):
    professional = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='schedule_blocks',
        verbose_name='Profissional',
    )
    block_type = models.CharField(
        'Tipo de bloqueio',
        max_length=25,
        choices=ScheduleBlockTypeChoices.choices,
        default=ScheduleBlockTypeChoices.ABSENCE,
    )
    start_at = models.DateTimeField('Início do bloqueio')
    end_at = models.DateTimeField('Fim do bloqueio')
    reason = models.CharField('Motivo / Observação', max_length=160, blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_schedule_blocks',
        verbose_name='Registrado por',
    )

    class Meta:
        verbose_name = 'Bloqueio de agenda'
        verbose_name_plural = 'Bloqueios de agenda'
        ordering = ['-start_at']

    def __str__(self):
        return (
            f'{self.professional.full_name} ({self.get_block_type_display()}): '
            f'{self.start_at} até {self.end_at}'
        )

    def overlaps(self, interval_start, interval_end):
        return self.start_at < interval_end and self.end_at > interval_start

    def clean(self):
        super().clean()
        if self.professional_id and self.salon_id:
            if self.professional.salon_id != self.salon_id:
                raise ValidationError(
                    {'professional': 'O profissional selecionado não pertence a este salão.'}
                )
        if self.start_at and self.end_at and self.start_at >= self.end_at:
            raise ValidationError(
                {'end_at': 'A data/hora final do bloqueio deve ser posterior à data/hora inicial.'}
            )


class Appointment(TenantScopedModel):
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name='Cliente',
    )
    professional = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name='Profissional',
    )
    start_at = models.DateTimeField('Início do agendamento')
    end_at = models.DateTimeField('Fim estimado do agendamento')
    total_duration_minutes = models.PositiveIntegerField(
        'Duração total estimada (min)',
        default=30,
    )
    total_estimated_amount = models.DecimalField(
        'Valor total estimado (R$)',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    status = models.CharField(
        'Status',
        max_length=25,
        choices=AppointmentStatusChoices.choices,
        default=AppointmentStatusChoices.SCHEDULED,
    )
    notes = models.TextField('Observações', blank=True)
    public_token = models.UUIDField(
        'Token público',
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    cancellation_reason = models.CharField(
        'Motivo do cancelamento',
        max_length=200,
        blank=True,
    )
    cancelled_at = models.DateTimeField('Cancelado em', null=True, blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_appointments',
        verbose_name='Criado por',
    )

    class Meta:
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
        ordering = ['start_at']
        indexes = [
            models.Index(
                fields=['salon', 'professional', 'start_at', 'end_at'],
                name='idx_appt_salon_prof_interval',
            ),
        ]

    def __str__(self):
        return (
            f'{self.client.full_name} com {self.professional.full_name} — '
            f'{self.start_at:%d/%m/%Y %H:%M} ({self.get_status_display()})'
        )

    def overlaps(self, interval_start, interval_end):
        return self.start_at < interval_end and self.end_at > interval_start

    def recalculate_totals_from_items(self):
        items = list(self.items.all())
        total_minutes = sum(item.duration_minutes_snapshot for item in items)
        total_amount = sum(
            (item.price_snapshot for item in items),
            Decimal('0.00'),
        )
        self.total_duration_minutes = total_minutes
        self.total_estimated_amount = total_amount
        if self.start_at and total_minutes > 0:
            self.end_at = self.start_at + timedelta(minutes=total_minutes)

    def clean(self):
        super().clean()
        errors = {}
        if self.client_id and self.salon_id:
            if self.client.salon_id != self.salon_id:
                errors['client'] = 'O cliente selecionado pertence a outro salão.'
        if self.professional_id and self.salon_id:
            if self.professional.salon_id != self.salon_id:
                errors['professional'] = 'O profissional selecionado pertence a outro salão.'
        if self.start_at and self.end_at and self.start_at >= self.end_at:
            errors['end_at'] = 'O horário de término deve ser posterior ao horário de início.'
        if errors:
            raise ValidationError(errors)


class AppointmentItem(TenantScopedModel):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Agendamento',
    )
    service = models.ForeignKey(
        'catalog.Service',
        on_delete=models.PROTECT,
        related_name='appointment_items',
        verbose_name='Serviço',
    )
    duration_minutes_snapshot = models.PositiveIntegerField(
        'Duração no agendamento (min)',
    )
    price_snapshot = models.DecimalField(
        'Preço no agendamento (R$)',
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        verbose_name = 'Item de serviço do agendamento'
        verbose_name_plural = 'Itens de serviço do agendamento'
        ordering = ['id']

    def __str__(self):
        return (
            f'{self.service.name} ({self.duration_minutes_snapshot} min - '
            f'R$ {self.price_snapshot})'
        )

    def clean(self):
        super().clean()
        errors = {}
        if self.appointment_id and self.salon_id:
            if self.appointment.salon_id != self.salon_id:
                errors['appointment'] = 'O agendamento selecionado pertence a outro salão.'
        if self.service_id and self.salon_id:
            if self.service.salon_id != self.salon_id:
                errors['service'] = 'O serviço selecionado pertence a outro salão.'
        if errors:
            raise ValidationError(errors)
