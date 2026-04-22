from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, Optional

from django.db import connection
from django.utils import timezone
from zoneinfo import ZoneInfo

from notifications.choices import NotificationType
from notifications.models import (
    KidBirthdayNotification,
    NotificationSchedule,
    NotificationTemplate,
    StoryRecipientConfig,
)
from utils.avatariya_client import AvatariyaClient
from utils.mobile_client import MobileClient

ALMATY_TZ = ZoneInfo('Asia/Almaty')


@dataclass(frozen=True)
class CollectResult:
    created: int
    updated: int
    skipped: int


@dataclass(frozen=True)
class RecipientDispatchResult:
    resolved_phone: str
    guest_payload: Dict[str, Any]
    story_created: bool
    external_story_id: Optional[int]
    last_error: str


class KidBirthdayFlowService:
    def __init__(self) -> None:
        self.avatariya_client = AvatariyaClient()
        self.mobile_client = MobileClient()

    def collect_due_birthdays(self, notification_type: str = NotificationType.HB_KIDS) -> CollectResult:
        schedule = NotificationSchedule.objects.filter(notification_type=notification_type, enabled=True).first()
        if not schedule:
            return CollectResult(created=0, updated=0, skipped=0)

        now_local = timezone.now().astimezone(ALMATY_TZ)
        queue_create_time = schedule.queue_create_time or schedule.send_time

        if now_local.time() < queue_create_time:
            return CollectResult(created=0, updated=0, skipped=0)

        last_checked_at = schedule.last_checked_at
        if last_checked_at is not None and last_checked_at.astimezone(ALMATY_TZ).date() == now_local.date():
            return CollectResult(created=0, updated=0, skipped=0)

        return self.collect_today_birthdays(notification_type=notification_type)

    def collect_today_birthdays(self, notification_type: str = NotificationType.HB_KIDS) -> CollectResult:
        schedule = NotificationSchedule.objects.filter(notification_type=notification_type, enabled=True).first()
        if not schedule:
            return CollectResult(created=0, updated=0, skipped=0)

        check_started_at = timezone.now()

        now_local = timezone.now().astimezone(ALMATY_TZ)
        today = now_local.date()
        dob_day = today.strftime('%d-%m')
        kids = self.avatariya_client.get_kids_by_dob_day(dob_day)

        scheduled_for_local = datetime.combine(today, schedule.send_time, tzinfo=ALMATY_TZ)

        created = 0
        updated = 0
        skipped = 0
        latest_queue_created_at = None

        for kid in kids:
            kid_id = kid.get('id')
            guest_id = kid.get('guest')
            if not kid_id or not guest_id:
                skipped += 1
                continue

            guest_payload: Dict[str, Any] = {}
            guest_phone = ''
            try:
                guest_payload = self.avatariya_client.get_guest(int(guest_id))
                guest_phone = str(guest_payload.get('phone') or '').strip()
            except Exception:
                # If guest payload is unavailable we cannot validate mobile_app, so skip queue entry.
                skipped += 1
                continue

            if not self._is_mobile_app_enabled(guest_payload):
                skipped += 1
                continue

            obj, was_created = KidBirthdayNotification.objects.update_or_create(
                notification_type=notification_type,
                schedule_date=today,
                kid_id=int(kid_id),
                defaults={
                    'birthday_date': _parse_date(kid.get('dob')),
                    'kid_name': str(kid.get('name') or '').strip(),
                    'guest_id': int(guest_id),
                    'guest_phone': guest_phone,
                    'scheduled_for': scheduled_for_local,
                    'kid_payload': kid,
                    'guest_payload': guest_payload,
                },
            )
            if was_created:
                created += 1
                if obj.created_at and (latest_queue_created_at is None or obj.created_at > latest_queue_created_at):
                    latest_queue_created_at = obj.created_at
            elif not obj.sent:
                updated += 1

        schedule.last_checked_at = check_started_at
        if latest_queue_created_at is not None:
            schedule.last_queue_entry_created_at = latest_queue_created_at
        schedule.save(update_fields=['last_checked_at', 'last_queue_entry_created_at', 'updated_at'])

        return CollectResult(created=created, updated=updated, skipped=skipped)

    def dispatch_due_notifications(self, notification_type: str = NotificationType.HB_KIDS, limit: int = 200) -> Dict[str, int]:
        template = NotificationTemplate.objects.filter(notification_type=notification_type, enabled=True).first()
        schedule = NotificationSchedule.objects.filter(notification_type=notification_type, enabled=True).first()
        story_config, story_date = self._load_story_config(notification_type)

        if not template or not schedule:
            return {'sent': 0, 'failed': 0, 'skipped': 0}

        now = timezone.now()
        today_local = now.astimezone(ALMATY_TZ).date()
        candidate_rows = list(
            KidBirthdayNotification.objects.filter(
                notification_type=notification_type,
                schedule_date=today_local,
                sent=False,
                scheduled_for__lte=now,
                last_error='',
                processing_started_at__isnull=True,
            )
            .order_by('scheduled_for', 'id')
            .only('id', 'notification_type', 'schedule_date', 'guest_id', 'guest_phone')
        )
        candidate_ids = self._choose_recipient_candidates(candidate_rows, limit=limit)

        sent = 0
        failed = 0
        skipped = 0

        for item_id in candidate_ids:
            base_item = KidBirthdayNotification.objects.filter(id=item_id).first()
            if not base_item:
                skipped += 1
                continue

            group_ids = self._pending_group_ids(base_item, now=now)
            if not group_ids:
                skipped += 1
                continue

            claimed = KidBirthdayNotification.objects.filter(
                id__in=group_ids,
                sent=False,
                last_error='',
                processing_started_at__isnull=True,
            ).update(processing_started_at=timezone.now())
            if not claimed:
                skipped += 1
                continue

            group_rows = list(KidBirthdayNotification.objects.filter(id__in=group_ids).order_by('id'))
            dispatch_item = self._pick_dispatch_item(group_rows)

            existing_sent = self._find_existing_sent(dispatch_item)
            if existing_sent:
                self._mark_group_already_sent(group_ids=group_ids, existing=existing_sent)
                skipped += 1
                continue

            try:
                result = self._dispatch_single(
                    item=dispatch_item,
                    template=template,
                    story_config=story_config,
                    story_date=story_date,
                )
                self._mark_group_sent(group_ids=group_ids, result=result)
                sent += 1
            except Exception as exc:
                self._mark_group_failed(group_ids=group_ids, error=str(exc))
                failed += 1
                continue

        return {'sent': sent, 'failed': failed, 'skipped': skipped}

    def _dispatch_single(
        self,
        item: KidBirthdayNotification,
        template: NotificationTemplate,
        story_config: StoryRecipientConfig | None,
        story_date: Optional[date],
    ) -> RecipientDispatchResult:
        if story_config and story_date and story_date != item.schedule_date:
            raise ValueError(
                f'Story date mismatch: story_date={story_date} '
                f'!= schedule_date={item.schedule_date}'
            )

        phone = (item.guest_phone or '').strip()
        guest_payload: Dict[str, Any] = dict(item.guest_payload or {})
        if not phone:
            guest_payload = self.avatariya_client.get_guest(item.guest_id)
            phone = str(guest_payload.get('phone') or '').strip()

        if not phone:
            raise ValueError('Guest phone is empty')

        notification_id = self.mobile_client.send_mass_push(
            phone_numbers=[phone],
            title=template.title,
            body=template.body,
            title_kz=template.title_kz,
            body_kz=template.body_kz,
            city=template.city,
            park=template.park,
            notification_type=template.notification_backend_type,
            survey_id=template.survey_id,
            review_id=template.review_id,
        )

        story_created = False
        external_story_id: Optional[int] = None
        story_error = ''

        if story_config:
            try:
                recipient = self.mobile_client.create_story_recipient(
                    phone_number=phone,
                    story_id=int(story_config.story_id),
                    notification_id=notification_id,
                )
                # API may return created=false when recipient already exists; treat this as success.
                story_created = True
                external_story_id = int(recipient.get('story_id') or story_config.story_id)
            except Exception as exc:
                # Push already sent successfully. Keep sent state and prevent re-send.
                story_created = False
                external_story_id = int(story_config.story_id)
                story_error = f'Story recipient create failed after push send: {exc}'
        else:
            story_created = False
            external_story_id = None

        return RecipientDispatchResult(
            resolved_phone=phone,
            guest_payload=guest_payload,
            story_created=story_created,
            external_story_id=external_story_id,
            last_error=story_error,
        )

    def _choose_recipient_candidates(self, rows: Iterable[KidBirthdayNotification], limit: int) -> list[int]:
        candidate_ids: list[int] = []
        seen_keys = set()

        for row in rows:
            key = self._recipient_key(row)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            candidate_ids.append(row.id)
            if len(candidate_ids) >= limit:
                break

        return candidate_ids

    def _pending_group_ids(self, item: KidBirthdayNotification, now) -> list[int]:
        qs = KidBirthdayNotification.objects.filter(
            notification_type=item.notification_type,
            schedule_date=item.schedule_date,
            sent=False,
            last_error='',
            processing_started_at__isnull=True,
            scheduled_for__lte=now,
        )

        if item.guest_id:
            qs = qs.filter(guest_id=item.guest_id)
        elif item.guest_phone:
            qs = qs.filter(guest_phone=item.guest_phone)
        else:
            qs = qs.filter(id=item.id)

        return list(qs.values_list('id', flat=True))

    def _pick_dispatch_item(self, rows: list[KidBirthdayNotification]) -> KidBirthdayNotification:
        for row in rows:
            if (row.guest_phone or '').strip():
                return row
        return rows[0]

    def _mark_group_sent(self, group_ids: list[int], result: RecipientDispatchResult) -> None:
        now = timezone.now()
        KidBirthdayNotification.objects.filter(id__in=group_ids).update(
            sent=True,
            sent_at=now,
            guest_phone=result.resolved_phone,
            guest_payload=result.guest_payload,
            story_created=result.story_created,
            external_story_id=result.external_story_id,
            last_error=result.last_error,
            processing_started_at=None,
            updated_at=now,
        )

    def _mark_group_failed(self, group_ids: list[int], error: str) -> None:
        now = timezone.now()
        KidBirthdayNotification.objects.filter(id__in=group_ids).update(
            last_error=error,
            processing_started_at=None,
            updated_at=now,
        )

    def _mark_group_already_sent(self, group_ids: list[int], existing: KidBirthdayNotification) -> None:
        now = timezone.now()
        KidBirthdayNotification.objects.filter(id__in=group_ids).update(
            sent=True,
            sent_at=existing.sent_at or now,
            guest_phone=existing.guest_phone,
            guest_payload=existing.guest_payload,
            story_created=existing.story_created,
            external_story_id=existing.external_story_id,
            last_error=existing.last_error,
            processing_started_at=None,
            updated_at=now,
        )

    def _recipient_key(self, row: KidBirthdayNotification) -> str:
        if row.guest_id:
            return f'guest:{row.guest_id}'

        digits = ''.join(ch for ch in str(row.guest_phone or '') if ch.isdigit())
        if digits:
            return f'phone:{digits}'

        return f'row:{row.id}'

    def _find_existing_sent(self, row: KidBirthdayNotification) -> Optional[KidBirthdayNotification]:
        qs = KidBirthdayNotification.objects.filter(
            notification_type=row.notification_type,
            schedule_date=row.schedule_date,
            sent=True,
        ).order_by('sent_at', 'id')

        if row.guest_id:
            return qs.filter(guest_id=row.guest_id).first()

        digits = ''.join(ch for ch in str(row.guest_phone or '') if ch.isdigit())
        if digits:
            return qs.filter(guest_phone=row.guest_phone).first()

        return None

    def _load_story_config(self, notification_type: str) -> tuple[Optional[StoryRecipientConfig], Optional[date]]:
        try:
            config = (
                StoryRecipientConfig.objects.filter(notification_type=notification_type, enabled=True)
                .only('id', 'notification_type', 'story_id', 'enabled')
                .first()
            )
        except Exception:
            return None, None

        if not config:
            return None, None

        story_date = None
        if self._story_date_column_exists():
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT story_date FROM notifications_storyrecipientconfig WHERE id = %s',
                        [config.id],
                    )
                    row = cursor.fetchone()
                    story_date = row[0] if row else None
            except Exception:
                story_date = None

        return config, story_date

    def _story_date_column_exists(self) -> bool:
        try:
            with connection.cursor() as cursor:
                columns = {
                    col.name
                    for col in connection.introspection.get_table_description(
                        cursor,
                        StoryRecipientConfig._meta.db_table,
                    )
                }
            return 'story_date' in columns
        except Exception:
            return False

    def _is_mobile_app_enabled(self, guest_payload: Dict[str, Any]) -> bool:
        value = guest_payload.get('mobile_app')
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() in {'1', 'true', 'yes', 'y'}

        if isinstance(value, (int, float)):
            return bool(value)

        return False


def _parse_date(value: Any):
    if not value:
        return timezone.now().date()
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return timezone.now().date()
