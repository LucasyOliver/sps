from datetime import datetime, time, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from accounts.models import User, UserRoleChoices
from clients.models import Client, normalize_digits
from salons.models import SalonBusinessHours, SalonHoliday
from scheduling.models import (
    ACTIVE_APPOINTMENT_STATUSES,
    Appointment,
    AppointmentItem,
    AppointmentStatusChoices,
    ProfessionalSchedule,
    ScheduleBlock,
)


ALLOWED_STATUS_TRANSITIONS = {
    AppointmentStatusChoices.SCHEDULED: {
        AppointmentStatusChoices.CONFIRMED,
        AppointmentStatusChoices.IN_PROGRESS,
        AppointmentStatusChoices.CANCELLED,
        AppointmentStatusChoices.NO_SHOW,
    },
    AppointmentStatusChoices.CONFIRMED: {
        AppointmentStatusChoices.IN_PROGRESS,
        AppointmentStatusChoices.COMPLETED,
        AppointmentStatusChoices.CANCELLED,
        AppointmentStatusChoices.NO_SHOW,
    },
    AppointmentStatusChoices.IN_PROGRESS: {
        AppointmentStatusChoices.COMPLETED,
        AppointmentStatusChoices.CANCELLED,
    },
    AppointmentStatusChoices.COMPLETED: set(),
    AppointmentStatusChoices.CANCELLED: set(),
    AppointmentStatusChoices.NO_SHOW: set(),
}


class AvailabilityService:
    """
    Motor de disponibilidade de agenda (S04-T02).
    Calcula janelas e horários livres considerando:
      - Feriados/fechamentos do salão (SalonHoliday)
      - Expediente semanal do salão (SalonBusinessHours)
      - Expediente individual e intervalo do profissional (ProfessionalSchedule)
      - Bloqueios de agenda (ScheduleBlock)
      - Agendamentos ativos (agendado, confirmado, em_atendimento)
    """

    @staticmethod
    def ensure_aware(dt: datetime) -> datetime:
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return timezone.localtime(dt, timezone.get_current_timezone())

    @classmethod
    def validate_interval_available(
        cls,
        *,
        salon,
        professional,
        start_at: datetime,
        end_at: datetime,
        exclude_appointment_id=None,
    ) -> None:
        local_start = cls.ensure_aware(start_at)
        local_end = cls.ensure_aware(end_at)

        if local_start >= local_end:
            raise ValidationError(
                'O horário de término deve ser posterior ao horário de início.'
            )

        if local_start.date() != local_end.date():
            raise ValidationError(
                'O agendamento deve iniciar e terminar no mesmo dia de expediente.'
            )

        target_date = local_start.date()
        weekday = target_date.weekday()
        start_t = local_start.time()
        end_t = local_end.time()

        # 1. Feriados / fechamentos do salão
        holiday = SalonHoliday.objects.for_salon(salon).filter(
            date=target_date,
        ).first()
        if holiday is not None:
            if holiday.is_closed_all_day:
                raise ValidationError(
                    'O salão estará fechado na data selecionada (feriado/fechamento).'
                )
            if (
                holiday.opening_time
                and holiday.closing_time
                and (start_t < holiday.opening_time or end_t > holiday.closing_time)
            ):
                raise ValidationError(
                    'O horário solicitado está fora do expediente especial de feriado do salão.'
                )

        # 2. Expediente semanal do salão
        salon_hours = SalonBusinessHours.objects.for_salon(salon).filter(
            weekday=weekday,
        ).first()
        if salon_hours is not None:
            if not salon_hours.is_open:
                raise ValidationError('O salão está fechado neste dia da semana.')
            if start_t < salon_hours.opening_time or end_t > salon_hours.closing_time:
                raise ValidationError(
                    'O horário solicitado está fora do expediente de funcionamento do salão.'
                )

        # 3. Expediente individual e intervalo do profissional
        prof_schedule = ProfessionalSchedule.objects.for_salon(salon).filter(
            professional=professional,
            weekday=weekday,
        ).first()
        if prof_schedule is not None:
            if not prof_schedule.is_working:
                raise ValidationError(
                    'O profissional não possui expediente ativo neste dia da semana.'
                )
            if start_t < prof_schedule.start_time or end_t > prof_schedule.end_time:
                raise ValidationError(
                    'O horário solicitado está fora do expediente individual do profissional.'
                )
            if prof_schedule.break_start_time and prof_schedule.break_end_time:
                if (
                    start_t < prof_schedule.break_end_time
                    and end_t > prof_schedule.break_start_time
                ):
                    raise ValidationError(
                        'O horário solicitado conflita com o intervalo de descanso do profissional.'
                    )

        # 4. Bloqueios de agenda (férias, folgas, ausências)
        overlapping_blocks = ScheduleBlock.objects.for_salon(salon).filter(
            professional=professional,
            start_at__lt=local_end,
            end_at__gt=local_start,
        )
        if overlapping_blocks.exists():
            raise ValidationError(
                'O profissional possui um bloqueio de agenda (férias, folga ou ausência) neste horário.'
            )

        # 5. Agendamentos ativos existentes
        overlapping_appts = Appointment.objects.for_salon(salon).filter(
            professional=professional,
            status__in=ACTIVE_APPOINTMENT_STATUSES,
            start_at__lt=local_end,
            end_at__gt=local_start,
        )
        if exclude_appointment_id is not None:
            overlapping_appts = overlapping_appts.exclude(pk=exclude_appointment_id)

        if overlapping_appts.exists():
            raise ValidationError(
                'Conflito de horário: o profissional já possui um agendamento ativo neste intervalo.'
            )

    @classmethod
    def get_available_slots(
        cls,
        *,
        salon,
        professional,
        target_date,
        services=None,
        duration_minutes: int | None = None,
        slot_step_minutes: int = 15,
        exclude_appointment_id=None,
    ) -> list[datetime]:
        if services:
            total_duration = sum(int(s.duration_minutes) for s in services)
        else:
            total_duration = int(duration_minutes or 30)

        if total_duration <= 0:
            return []

        holiday = SalonHoliday.objects.for_salon(salon).filter(
            date=target_date,
        ).first()
        if holiday is not None and holiday.is_closed_all_day:
            return []

        weekday = target_date.weekday()
        salon_hours = SalonBusinessHours.objects.for_salon(salon).filter(
            weekday=weekday,
        ).first()
        if salon_hours is not None and not salon_hours.is_open:
            return []

        prof_schedule = ProfessionalSchedule.objects.for_salon(salon).filter(
            professional=professional,
            weekday=weekday,
        ).first()
        if prof_schedule is not None and not prof_schedule.is_working:
            return []

        window_start_time = time(9, 0)
        window_end_time = time(18, 0)

        if salon_hours is not None:
            window_start_time = salon_hours.opening_time
            window_end_time = salon_hours.closing_time

        if (
            holiday is not None
            and not holiday.is_closed_all_day
            and holiday.opening_time
            and holiday.closing_time
        ):
            window_start_time = max(window_start_time, holiday.opening_time)
            window_end_time = min(window_end_time, holiday.closing_time)

        if prof_schedule is not None:
            window_start_time = max(window_start_time, prof_schedule.start_time)
            window_end_time = min(window_end_time, prof_schedule.end_time)

        if window_start_time >= window_end_time:
            return []

        tz = timezone.get_current_timezone()
        day_start = timezone.make_aware(
            datetime.combine(target_date, window_start_time), tz
        )
        day_end = timezone.make_aware(
            datetime.combine(target_date, window_end_time), tz
        )

        blocks = list(
            ScheduleBlock.objects.for_salon(salon).filter(
                professional=professional,
                start_at__lt=day_end,
                end_at__gt=day_start,
            )
        )
        appointments_qs = Appointment.objects.for_salon(salon).filter(
            professional=professional,
            status__in=ACTIVE_APPOINTMENT_STATUSES,
            start_at__lt=day_end,
            end_at__gt=day_start,
        )
        if exclude_appointment_id is not None:
            appointments_qs = appointments_qs.exclude(pk=exclude_appointment_id)
        appointments = list(appointments_qs)

        available_slots = []
        cursor = day_start
        duration_delta = timedelta(minutes=total_duration)
        step_delta = timedelta(minutes=slot_step_minutes)

        while cursor + duration_delta <= day_end:
            candidate_end = cursor + duration_delta
            cand_start_t = cursor.time()
            cand_end_t = candidate_end.time()

            conflict = False
            if (
                prof_schedule is not None
                and prof_schedule.break_start_time
                and prof_schedule.break_end_time
            ):
                if (
                    cand_start_t < prof_schedule.break_end_time
                    and cand_end_t > prof_schedule.break_start_time
                ):
                    conflict = True

            if not conflict:
                for block in blocks:
                    if block.overlaps(cursor, candidate_end):
                        conflict = True
                        break

            if not conflict:
                for appt in appointments:
                    if appt.overlaps(cursor, candidate_end):
                        conflict = True
                        break

            if not conflict:
                available_slots.append(cursor)

            cursor += step_delta

        return available_slots


class SchedulingService:
    """
    Serviço transacional da Agenda Inteligente (S04-T03, RF-005, RNF-002).
    Utiliza transaction.atomic() e select_for_update() no profissional para impedir
    double-booking e gerenciar o ciclo de vida do agendamento.
    """

    @staticmethod
    def _validate_entities_and_compute_totals(salon, client, professional, services):
        if salon is None:
            raise ValidationError('Salão é obrigatório para agendar.')
        if client is None or client.salon_id != salon.id or not client.is_active:
            raise ValidationError(
                {'client': 'Cliente inválido, inativo ou pertencente a outro salão.'}
            )
        if (
            professional is None
            or professional.salon_id != salon.id
            or not professional.is_active
            or professional.role
            not in (UserRoleChoices.PROFISSIONAL, UserRoleChoices.GESTOR)
        ):
            raise ValidationError(
                {'professional': 'Profissional inválido, inativo ou pertencente a outro salão.'}
            )

        service_list = list(services or [])
        if not service_list:
            raise ValidationError(
                {'services': 'Selecione pelo menos um serviço para o agendamento.'}
            )

        total_duration = 0
        total_amount = Decimal('0.00')
        for service in service_list:
            if service.salon_id != salon.id or not service.is_active:
                raise ValidationError(
                    {'services': f'O serviço "{service.name}" não pertence a este salão ou está inativo.'}
                )
            if (
                service.professionals.exists()
                and not service.professionals.filter(pk=professional.pk).exists()
            ):
                raise ValidationError(
                    {
                        'services': (
                            f'O profissional {professional.full_name} não está habilitado '
                            f'para realizar o serviço "{service.name}".'
                        )
                    }
                )
            total_duration += int(service.duration_minutes)
            total_amount += service.base_price

        return service_list, total_duration, total_amount

    @classmethod
    def create_appointment(
        cls,
        *,
        salon,
        client,
        professional,
        start_at: datetime,
        services,
        notes: str = '',
        created_by=None,
        initial_status: str = AppointmentStatusChoices.SCHEDULED,
    ) -> Appointment:
        local_start = AvailabilityService.ensure_aware(start_at)

        with transaction.atomic():
            locked_prof = (
                User.objects.select_for_update()
                .filter(pk=getattr(professional, 'pk', None), salon=salon)
                .first()
            )
            service_list, total_duration, total_amount = (
                cls._validate_entities_and_compute_totals(
                    salon, client, locked_prof, services
                )
            )
            local_end = local_start + timedelta(minutes=total_duration)

            AvailabilityService.validate_interval_available(
                salon=salon,
                professional=locked_prof,
                start_at=local_start,
                end_at=local_end,
            )

            appointment = Appointment(
                salon=salon,
                client=client,
                professional=locked_prof,
                start_at=local_start,
                end_at=local_end,
                total_duration_minutes=total_duration,
                total_estimated_amount=total_amount,
                status=initial_status,
                notes=notes,
                created_by=created_by,
            )
            appointment.full_clean()
            appointment.save()

            for service in service_list:
                item = AppointmentItem(
                    salon=salon,
                    appointment=appointment,
                    service=service,
                    duration_minutes_snapshot=service.duration_minutes,
                    price_snapshot=service.base_price,
                )
                item.full_clean()
                item.save()

            return appointment

    @classmethod
    def reschedule_appointment(
        cls,
        *,
        appointment: Appointment,
        new_start_at: datetime,
        new_professional=None,
        new_services=None,
        notes: str | None = None,
    ) -> Appointment:
        if appointment.status not in ACTIVE_APPOINTMENT_STATUSES:
            raise ValidationError(
                'Apenas agendamentos ativos (agendado, confirmado ou em atendimento) podem ser remarcados.'
            )

        target_prof = new_professional or appointment.professional
        local_start = AvailabilityService.ensure_aware(new_start_at)

        with transaction.atomic():
            locked_prof = (
                User.objects.select_for_update()
                .filter(pk=getattr(target_prof, 'pk', None), salon=appointment.salon)
                .first()
            )

            if new_services is not None:
                service_list, total_duration, total_amount = (
                    cls._validate_entities_and_compute_totals(
                        appointment.salon,
                        appointment.client,
                        locked_prof,
                        new_services,
                    )
                )
            else:
                existing_services = [
                    item.service for item in appointment.items.select_related('service')
                ]
                service_list, total_duration, total_amount = (
                    cls._validate_entities_and_compute_totals(
                        appointment.salon,
                        appointment.client,
                        locked_prof,
                        existing_services,
                    )
                )
                total_duration = appointment.total_duration_minutes
                total_amount = appointment.total_estimated_amount

            local_end = local_start + timedelta(minutes=total_duration)

            AvailabilityService.validate_interval_available(
                salon=appointment.salon,
                professional=locked_prof,
                start_at=local_start,
                end_at=local_end,
                exclude_appointment_id=appointment.pk,
            )

            appointment.professional = locked_prof
            appointment.start_at = local_start
            appointment.end_at = local_end
            appointment.total_duration_minutes = total_duration
            appointment.total_estimated_amount = total_amount
            if notes is not None:
                appointment.notes = notes
            appointment.full_clean()
            appointment.save()

            if new_services is not None:
                appointment.items.all().delete()
                for service in service_list:
                    item = AppointmentItem(
                        salon=appointment.salon,
                        appointment=appointment,
                        service=service,
                        duration_minutes_snapshot=service.duration_minutes,
                        price_snapshot=service.base_price,
                    )
                    item.full_clean()
                    item.save()

            return appointment

    @classmethod
    def transition_status(
        cls,
        *,
        appointment: Appointment,
        new_status: str,
        cancellation_reason: str = '',
    ) -> Appointment:
        allowed_next = ALLOWED_STATUS_TRANSITIONS.get(appointment.status, set())
        if new_status not in allowed_next:
            raise ValidationError(
                f'Transição de status inválida de "{appointment.get_status_display()}" '
                f'para "{dict(AppointmentStatusChoices.choices).get(new_status, new_status)}".'
            )

        if new_status == AppointmentStatusChoices.CANCELLED:
            reason_clean = (cancellation_reason or '').strip()
            if not reason_clean:
                raise ValidationError(
                    {'cancellation_reason': 'Informe o motivo do cancelamento.'}
                )
            appointment.cancellation_reason = reason_clean
            appointment.cancelled_at = timezone.now()

        appointment.status = new_status
        appointment.full_clean()
        appointment.save()
        return appointment

    @classmethod
    def upsert_public_client(
        cls,
        *,
        salon,
        full_name: str,
        phone: str,
        email: str = '',
        cpf_cnpj: str = '',
    ) -> Client:
        phone_digits = normalize_digits(phone)
        if len(phone_digits) not in (10, 11):
            raise ValidationError(
                {'client_phone': 'O telefone deve conter 10 ou 11 dígitos numéricos (com DDD).'}
            )

        doc_digits = normalize_digits(cpf_cnpj)
        if doc_digits and len(doc_digits) not in (11, 14):
            raise ValidationError(
                {'client_cpf_cnpj': 'Informe um CPF válido (11 dígitos) ou CNPJ válido (14 dígitos).'}
            )

        existing = Client.objects.for_salon(salon).filter(phone=phone_digits).first()
        if existing is None and doc_digits:
            existing = (
                Client.objects.for_salon(salon).filter(cpf_cnpj=doc_digits).first()
            )

        if existing is not None:
            existing.full_name = (full_name or '').strip() or existing.full_name
            existing.phone = phone_digits
            if email and email.strip():
                existing.email = email.strip()
            if doc_digits:
                existing.cpf_cnpj = doc_digits
            existing.is_active = True
            existing.full_clean()
            existing.save()
            return existing

        client = Client(
            salon=salon,
            full_name=(full_name or '').strip(),
            phone=phone_digits,
            email=(email or '').strip(),
            cpf_cnpj=doc_digits,
            is_active=True,
        )
        client.full_clean()
        client.save()
        return client

    @classmethod
    def create_public_appointment(
        cls,
        *,
        salon,
        professional,
        start_at: datetime,
        services,
        client_full_name: str,
        client_phone: str,
        client_email: str = '',
        client_cpf_cnpj: str = '',
        notes: str = '',
    ) -> Appointment:
        with transaction.atomic():
            client = cls.upsert_public_client(
                salon=salon,
                full_name=client_full_name,
                phone=client_phone,
                email=client_email,
                cpf_cnpj=client_cpf_cnpj,
            )
            return cls.create_appointment(
                salon=salon,
                client=client,
                professional=professional,
                start_at=start_at,
                services=services,
                notes=notes,
                created_by=None,
            )

    @classmethod
    def can_cancel_publicly(
        cls,
        *,
        appointment: Appointment,
        now: datetime | None = None,
    ) -> tuple[bool, datetime]:
        current_time = AvailabilityService.ensure_aware(now or timezone.now())
        min_hours = int(getattr(appointment.salon, 'cancellation_min_hours', 0) or 0)
        cutoff = AvailabilityService.ensure_aware(appointment.start_at) - timedelta(
            hours=min_hours
        )
        is_allowed = (
            appointment.status in ACTIVE_APPOINTMENT_STATUSES
            and current_time <= cutoff
        )
        return is_allowed, cutoff

    @classmethod
    def cancel_public_appointment(
        cls,
        *,
        salon,
        appointment: Appointment,
        cancellation_reason: str = '',
        now: datetime | None = None,
    ) -> Appointment:
        if salon is None or appointment.salon_id != salon.id:
            raise ValidationError('Agendamento inválido para este salão.')

        if appointment.status not in ACTIVE_APPOINTMENT_STATUSES:
            raise ValidationError(
                'Este agendamento já não está mais ativo para cancelamento.'
            )

        can_cancel, _cutoff = cls.can_cancel_publicly(
            appointment=appointment,
            now=now,
        )
        if not can_cancel:
            raise ValidationError(
                f'O prazo para cancelamento online encerrou (antecedência mínima de '
                f'{salon.cancellation_min_hours}h antes do atendimento). '
                f'Entre em contato diretamente com a recepção do salão.'
            )

        reason = (
            (cancellation_reason or '').strip()
            or 'Cancelado pelo cliente no portal público de autoagendamento.'
        )
        updated = cls.transition_status(
            appointment=appointment,
            new_status=AppointmentStatusChoices.CANCELLED,
            cancellation_reason=reason,
        )
        if now is not None:
            updated.cancelled_at = AvailabilityService.ensure_aware(now)
            updated.save(update_fields=['cancelled_at', 'updated_at'])
        return updated
