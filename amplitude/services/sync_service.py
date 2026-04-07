import hashlib
import time as time_module
from datetime import date, datetime, time, timedelta
from typing import Callable, Iterable, Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from amplitude.models import DailyDeviceActivity, DeviceVisitTime
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

    def sync_date_range(
        self,
        start_date: date,
        end_date: date,
        max_retries: int = 3,
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        """Синхронизировать все дни в диапазоне [start_date, end_date] включительно."""
        current_tz = timezone.get_current_timezone()
        today = timezone.localdate()

        total_processed = 0
        total_inserted = 0
        days_synced = []

        current = start_date
        while current <= end_date:
            day_start = timezone.make_aware(datetime.combine(current, time.min), current_tz)
            if current == today:
                day_end = timezone.localtime(timezone.now())
            else:
                day_end = timezone.make_aware(datetime.combine(current, time.max), current_tz)

            day_processed = 0
            day_inserted = 0
            last_error = None

            for attempt in range(1, max_retries + 1):
                try:
                    day_processed = 0
                    day_inserted = 0
                    for event in self.client.fetch_events(start=day_start, end=day_end):
                        day_processed += 1
                        day_inserted += self._process_event(event, current)
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt < max_retries:
                        time_module.sleep(5 * attempt)  # 5s, 10s между попытками

            days_synced.append({
                'date': current.isoformat(),
                'processed': day_processed,
                'inserted': day_inserted,
                'error': str(last_error) if last_error else None,
            })

            if progress_callback is not None:
                try:
                    progress_callback(days_synced[-1])
                except Exception:
                    # Progress output must not break the sync itself.
                    pass

            total_processed += day_processed
            total_inserted += day_inserted
            current += timedelta(days=1)

        return {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_processed': total_processed,
            'total_inserted': total_inserted,
            'days': days_synced,
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
            visit_created = self._upsert_daily_activity(
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

        return 1 if visit_created else 0

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
    ) -> bool:
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
                'first_seen': event_time,
                'last_seen': event_time,
            },
        )

        _, visit_created = DeviceVisitTime.objects.get_or_create(
            daily_activity=daily,
            event_time=event_time,
        )

        visit_datetimes = list(
            daily.visit_records.order_by('event_time').values_list('event_time', flat=True)
        )
        daily.visits_count = len(visit_datetimes)

        if visit_datetimes:
            daily.first_seen = visit_datetimes[0]
            daily.last_seen = visit_datetimes[-1]

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

        return visit_created

    def _extract_device_metadata(self, event: dict) -> tuple[str, str, str]:
        device_brand = self._clean_text(event.get('device_brand'))
        device_manufacturer = self._clean_text(event.get('device_manufacturer'))
        device_model = self._clean_text(event.get('device_model'))

        device_type = self._clean_text(event.get('device_type'))
        device_family = self._clean_text(event.get('device_family'))

        if not device_model:
            device_model = device_type or device_family

        if not device_brand:
            family_brand = device_family.replace(' Phone', '').strip() if device_family else ''
            if family_brand:
                device_brand = family_brand
            elif device_type:
                device_brand = device_type.split(' ')[0].strip()

        if not device_manufacturer:
            device_manufacturer = device_brand

        return device_brand, device_manufacturer, device_model

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
