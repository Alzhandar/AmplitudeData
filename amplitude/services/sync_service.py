import hashlib
from datetime import datetime, time
from typing import Iterable, Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from amplitude.models import DailyDeviceActivity, MobileSession
from utils.amplitude_client import AmplitudeExportClient


class AmplitudeSyncService:
    phone_candidate_keys = (
        'phone',
        'phone_number',
        'phoneNumber',
        'msisdn',
        'mobile',
        'number',
    )
    mobile_platforms = {'ios', 'android', 'mobile'}

    def __init__(self, client: Optional[AmplitudeExportClient] = None) -> None:
        self.client = client or AmplitudeExportClient()
        self.required_event_types = set(settings.AMPLITUDE_MOBILE_EVENT_TYPES)

    def sync_today_mobile_events(self) -> dict:
        now = timezone.localtime(timezone.now())
        current_tz = timezone.get_current_timezone()
        start_of_day = timezone.make_aware(datetime.combine(now.date(), time.min), current_tz)

        processed = 0
        inserted = 0

        for event in self.client.fetch_events(start=start_of_day, end=now):
            processed += 1
            inserted += self._process_event(event, now.date())

        return {
            'processed': processed,
            'inserted': inserted,
            'date': now.date().isoformat(),
        }

    def _process_event(self, event: dict, target_date) -> int:
        if not self._is_mobile_event(event, self.required_event_types):
            return 0

        device_id = str(event.get('device_id', '')).strip()
        if not device_id:
            return 0

        event_time = self._extract_event_time(event)
        if event_time.date() != target_date:
            return 0

        user_id = str(event.get('user_id', '')).strip()
        event_type = str(event.get('event_type', '')).strip()
        platform = str(event.get('platform', '')).strip().lower()
        phone_number = self._extract_phone_number(event)
        insert_id = str(event.get('insert_id', '')).strip()
        dedupe_key = self._build_dedupe_key(event, event_time)

        with transaction.atomic():
            _, created = MobileSession.objects.get_or_create(
                dedupe_key=dedupe_key,
                defaults={
                    'date': event_time.date(),
                    'event_time': event_time,
                    'event_type': event_type,
                    'user_id': user_id,
                    'device_id': device_id,
                    'phone_number': phone_number,
                    'platform': platform,
                    'insert_id': insert_id,
                    'raw_event': event,
                },
            )
            if not created:
                return 0

            self._upsert_daily_activity(
                date_value=event_time.date(),
                event_time=event_time,
                device_id=device_id,
                user_id=user_id,
                phone_number=phone_number,
                platform=platform,
            )

        return 1

    def _upsert_daily_activity(
        self,
        date_value,
        event_time,
        device_id: str,
        user_id: str,
        phone_number: str,
        platform: str,
    ) -> None:
        daily, _ = DailyDeviceActivity.objects.get_or_create(
            date=date_value,
            device_id=device_id,
            defaults={
                'user_id': user_id,
                'phone_number': phone_number,
                'platform': platform,
                'visits_count': 0,
                'visit_times': [],
                'first_seen': event_time,
                'last_seen': event_time,
            },
        )

        visit_time_iso = event_time.isoformat()
        visit_times = list(daily.visit_times or [])
        if visit_time_iso not in visit_times:
            visit_times.append(visit_time_iso)
            visit_times.sort()

        daily.visits_count = len(visit_times)
        daily.visit_times = visit_times
        daily.first_seen = min(filter(None, [daily.first_seen, event_time]))
        daily.last_seen = max(filter(None, [daily.last_seen, event_time]))

        if not daily.phone_number and phone_number:
            daily.phone_number = phone_number
        if not daily.user_id and user_id:
            daily.user_id = user_id
        if not daily.platform and platform:
            daily.platform = platform

        daily.save(
            update_fields=[
                'visits_count',
                'visit_times',
                'first_seen',
                'last_seen',
                'phone_number',
                'user_id',
                'platform',
                'updated_at',
            ]
        )

    def _extract_phone_number(self, event: dict) -> str:
        containers = [event, event.get('user_properties') or {}, event.get('event_properties') or {}]
        for container in containers:
            for key in self.phone_candidate_keys:
                value = container.get(key)
                if value:
                    return str(value)
        return ''

    def _extract_event_time(self, event: dict):
        milliseconds = event.get('time')
        if isinstance(milliseconds, (int, float)):
            dt = datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc)
            return timezone.localtime(dt)

        for key in ('event_time', 'server_received_time', 'client_event_time'):
            value = event.get(key)
            if isinstance(value, str):
                parsed = parse_datetime(value)
                if parsed is not None:
                    if timezone.is_naive(parsed):
                        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
                    return timezone.localtime(parsed)

        return timezone.localtime(timezone.now())

    def _is_mobile_event(self, event: dict, required_event_types: Iterable[str]) -> bool:
        platform = str(event.get('platform', '')).strip().lower()
        event_type = str(event.get('event_type', '')).strip()

        platform_match = platform in self.mobile_platforms
        if required_event_types:
            return platform_match and event_type in required_event_types
        return platform_match

    def _build_dedupe_key(self, event: dict, event_time) -> str:
        parts = [
            str(event.get('device_id', '')),
            str(event.get('user_id', '')),
            str(event.get('event_type', '')),
            str(event.get('insert_id', '')),
            event_time.isoformat(),
        ]
        return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()
