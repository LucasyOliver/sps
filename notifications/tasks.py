from celery import shared_task
from notifications.services import NotificationService


@shared_task(name='notifications.send_appointment_notification_task')
def send_appointment_notification_task(
    salon_id: int,
    appointment_id: int,
    notification_type: str,
    reference_window: str = '',
) -> dict:
    log, sent = NotificationService.dispatch_appointment_notification(
        salon_id=salon_id,
        appointment_id=appointment_id,
        notification_type=notification_type,
        reference_window=reference_window,
    )
    return {
        'log_id': log.pk if log else None,
        'status': log.status if log else 'not_found',
        'sent': sent,
    }


@shared_task(name='notifications.dispatch_upcoming_appointment_reminders_task')
def dispatch_upcoming_appointment_reminders_task(hours_ahead: int = 24) -> dict:
    sent_count = NotificationService.dispatch_upcoming_reminders(
        hours_ahead=hours_ahead,
    )
    return {'sent_count': sent_count}
