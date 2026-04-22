import logging

from billiard.exceptions import SoftTimeLimitExceeded
from celery import shared_task
from django.utils import timezone

from coupon_dispatch.models import CouponDispatchJob, CouponDispatchJobStatus
from coupon_dispatch.services.coupon_dispatch_service import CouponDispatchService

logger = logging.getLogger(__name__)


@shared_task(bind=True, soft_time_limit=600, time_limit=660)
def process_coupon_dispatch_job_task(self, job_id: int):
    logger.info('Starting coupon dispatch job task: job_id=%s', job_id)
    try:
        return CouponDispatchService().process_job(job_id)
    except SoftTimeLimitExceeded:
        logger.exception('Coupon dispatch job %s exceeded soft time limit', job_id)
        _mark_job_failed(
            job_id=job_id,
            message='Processing timeout exceeded. Job was automatically stopped.',
        )
        return {'job_id': job_id, 'status': 'failed', 'reason': 'timeout'}
    except Exception as exc:
        logger.exception('Coupon dispatch job %s failed in task wrapper: %s', job_id, exc)
        _mark_job_failed(job_id=job_id, message=f'Unhandled task error: {exc}')
        raise


def _mark_job_failed(*, job_id: int, message: str) -> None:
    job = CouponDispatchJob.objects.filter(id=job_id).first()
    if not job:
        return

    now = timezone.now()
    if job.status != CouponDispatchJobStatus.FAILED:
        job.status = CouponDispatchJobStatus.FAILED
    if not job.finished_at:
        job.finished_at = now

    extra = str(message or '').strip()
    if extra:
        existing = str(job.error_log or '').strip()
        job.error_log = f"{existing}\n{extra}".strip() if existing else extra

    job.save(update_fields=['status', 'finished_at', 'error_log', 'updated_at'])

