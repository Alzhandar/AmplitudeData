from celery import shared_task
from django.db import transaction
from django.utils import timezone

from amplitude.models import AmplitudeSyncSchedule
from amplitude.services.sync_service import AmplitudeSyncService


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def sync_amplitude_today(self):
    service = AmplitudeSyncService()
    return service.sync_today_mobile_events()


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def run_scheduled_sync(self):
    with transaction.atomic():
        schedule, _ = AmplitudeSyncSchedule.objects.select_for_update().get_or_create(
            pk=1,
            defaults={'enabled': True},
        )

        if not schedule.enabled:
            return {'status': 'skipped', 'reason': 'disabled'}

        now = timezone.localtime(timezone.now())
        if schedule.run_at.hour != now.hour or schedule.run_at.minute != now.minute:
            return {
                'status': 'skipped',
                'reason': 'not_scheduled_time',
                'scheduled_for': schedule.run_at.strftime('%H:%M'),
                'now': now.strftime('%H:%M'),
            }

        if schedule.last_run_on == now.date():
            return {'status': 'skipped', 'reason': 'already_ran_today', 'date': now.date().isoformat()}

        result = AmplitudeSyncService().sync_today_mobile_events()
        schedule.last_run_on = now.date()
        schedule.save(update_fields=['last_run_on', 'updated_at'])
        return {'status': 'ok', 'result': result}
