from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from amplitude.models import DailyDeviceActivity
from amplitude.services.bigdata_visit_service import BigDataVisitSyncService


class Command(BaseCommand):
    help = 'Синхронизировать и сохранить визиты BigData за диапазон дат'

    def add_arguments(self, parser):
        parser.add_argument('--start', required=True, help='Начальная дата YYYY-MM-DD')
        parser.add_argument('--end', required=True, help='Конечная дата YYYY-MM-DD')
        parser.add_argument('--force-refresh', action='store_true', help='Игнорировать кэш и перезапросить все телефоны')

    def handle(self, *args, **options):
        try:
            start_date = datetime.strptime(options['start'], '%Y-%m-%d').date()
            end_date = datetime.strptime(options['end'], '%Y-%m-%d').date()
        except ValueError as exc:
            raise CommandError(f'Неверный формат даты: {exc}') from exc

        if start_date > end_date:
            raise CommandError('--start должна быть <= --end')

        phones = list(
            DailyDeviceActivity.objects.filter(date__range=(start_date, end_date))
            .exclude(phone_number='')
            .values_list('phone_number', flat=True)
            .distinct()
        )

        self.stdout.write(self.style.NOTICE(
            f'Синхронизация BigData: {start_date} → {end_date}, телефонов={len(phones)}'
        ))

        result = BigDataVisitSyncService().sync_visits(
            start_date=start_date,
            end_date=end_date,
            phones=phones,
            force_refresh=bool(options['force_refresh']),
        )

        self.stdout.write(self.style.SUCCESS(
            'Готово: '
            f"phones_total={result['phones_total']}, "
            f"phones_fetched={result['phones_fetched']}, "
            f"rows_fetched={result['rows_fetched']}, "
            f"inserted={result['inserted']}, "
            f"updated={result['updated']}"
        ))
