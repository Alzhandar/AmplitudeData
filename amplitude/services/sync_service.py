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
    missing_markers = {'', 'none', 'null', 'undefined', 'nan'}

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

        device_id = self._clean_text(event.get('device_id'))
        if not device_id:
            return 0

        event_time = self._extract_event_time(event)
        if event_time.date() != target_date:
            return 0

        user_id = self._clean_text(event.get('user_id'))
        event_type = self._clean_text(event.get('event_type'))
        platform = self._clean_text(event.get('platform')).lower()
        device_brand, device_manufacturer, device_model = self._extract_device_metadata(event)
        phone_number = self._extract_phone_number(event)
        insert_id = self._clean_text(event.get('insert_id'))
        dedupe_key = self._build_dedupe_key(event, event_time)

        with transaction.atomic():
            session, created = MobileSession.objects.get_or_create(
                dedupe_key=dedupe_key,
                defaults={
                    'date': event_time.date(),
                    'event_time': event_time,
                    'event_type': event_type,
                    'user_id': user_id,
                    'device_id': device_id,
                    'phone_number': phone_number,
                    'platform': platform,
                    'device_brand': device_brand,
                    'device_manufacturer': device_manufacturer,
                    'device_model': device_model,
                    'insert_id': insert_id,
                    'raw_event': event,
                },
            )

            if not created:
                self._update_session_metadata(
                    session=session,
                    phone_number=phone_number,
                    platform=platform,
                    device_brand=device_brand,
                    device_manufacturer=device_manufacturer,
                    device_model=device_model,
                )

            self._upsert_daily_activity(
                date_value=event_time.date(),
                event_time=event_time,
                device_id=device_id,
                user_id=user_id,
                phone_number=phone_number,
                platform=platform,
                device_brand=device_brand,
                device_manufacturer=device_manufacturer,
                device_model=device_model,
            )

        return 1 if created else 0

    def _update_session_metadata(
        self,
        session: MobileSession,
        phone_number: str,
        platform: str,
        device_brand: str,
        device_manufacturer: str,
        device_model: str,
    ) -> None:
        fields_to_update = []

        if self._is_missing_text(session.phone_number) and phone_number:
            session.phone_number = phone_number
            fields_to_update.append('phone_number')
        if self._is_missing_text(session.platform) and platform:
            session.platform = platform
            fields_to_update.append('platform')
        if self._is_missing_text(session.device_brand) and device_brand:
            session.device_brand = device_brand
            fields_to_update.append('device_brand')
        if self._is_missing_text(session.device_manufacturer) and device_manufacturer:
            session.device_manufacturer = device_manufacturer
            fields_to_update.append('device_manufacturer')
        if self._is_missing_text(session.device_model) and device_model:
            session.device_model = device_model
            fields_to_update.append('device_model')

        if fields_to_update:
            session.save(update_fields=fields_to_update)

    def _upsert_daily_activity(
        self,
        date_value,
        event_time,
        device_id: str,
        user_id: str,
        phone_number: str,
        platform: str,
        device_brand: str,
        device_manufacturer: str,
        device_model: str,
    ) -> None:
        daily, _ = DailyDeviceActivity.objects.get_or_create(
            date=date_value,
            device_id=device_id,
            defaults={
                'user_id': user_id,
                'phone_number': phone_number,
                'platform': platform,
                'device_brand': device_brand,
                'device_manufacturer': device_manufacturer,
                'device_model': device_model,
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

        if self._is_missing_text(daily.phone_number) and phone_number:
            daily.phone_number = phone_number
        if self._is_missing_text(daily.user_id) and user_id:
            daily.user_id = user_id
        if self._is_missing_text(daily.platform) and platform:
            daily.platform = platform
        if self._is_missing_text(daily.device_brand) and device_brand:
            daily.device_brand = device_brand
        if self._is_missing_text(daily.device_manufacturer) and device_manufacturer:
            daily.device_manufacturer = device_manufacturer
        if self._is_missing_text(daily.device_model) and device_model:
            daily.device_model = device_model

        daily.save(
            update_fields=[
                'visits_count',
                'visit_times',
                'first_seen',
                'last_seen',
                'phone_number',
                'user_id',
                'platform',
                'device_brand',
                'device_manufacturer',
                'device_model',
                'updated_at',
            ]
        )

    def _extract_device_metadata(self, event: dict) -> tuple[str, str, str]:
        return (
            self._clean_text(event.get('device_brand')),
            self._clean_text(event.get('device_manufacturer')),
            self._clean_text(event.get('device_model')),
        )

    def _extract_phone_number(self, event: dict) -> str:
        containers = [event, event.get('user_properties') or {}, event.get('event_properties') or {}]
        for container in containers:
            for key in self.phone_candidate_keys:
                cleaned = self._clean_text(container.get(key))
                if cleaned:
                    return cleaned
        return ''

    def _clean_text(self, value) -> str:
        if value is None:
            return ''

        text = str(value).strip()
        if text.lower() in self.missing_markers:
            return ''
        return text

    def _is_missing_text(self, value: str) -> bool:
        return self._clean_text(value) == ''

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
