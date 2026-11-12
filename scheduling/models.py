from django.core.exceptions import ValidationError
from django.db import models
from base.models import TenantScopedModel
from salons.models import SalonBusinessHours, WeekdayChoices


class ScheduleBlockTypeChoices(models.TextChoices):
    VACATION = 'ferias', 'Férias'
    DAY_OFF = 'folga', 'Folga'
    ABSENCE = 'ausencia', 'Ausência / Compromisso'
    OTHER = 'outro', 'Outro bloqueio'


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
