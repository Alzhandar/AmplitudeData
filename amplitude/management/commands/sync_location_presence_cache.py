from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from amplitude.models import LocationPresenceStatsCache
from amplitude.services.location_presence_service import LocationPresenceAnalyticsService


class Command(BaseCommand):
    help = 'Предрасчет и сохранение кэша статистики присутствия за диапазон дат'

    def add_arguments(self, parser):
        parser.add_argument('--start', required=True, help='Начальная дата YYYY-MM-DD')
        parser.add_argument('--end', required=True, help='Конечная дата YYYY-MM-DD')
        parser.add_argument('--window-hours', type=int, default=24, help='Окно в часах (по умолчанию 24)')
        parser.add_argument('--sync', action='store_true', help='Перед расчетом выполнить sync BigData (только для малых диапазонов)')

    def handle(self, *args, **options):
        try:
            start_date = datetime.strptime(options['start'], '%Y-%m-%d').date()
            end_date = datetime.strptime(options['end'], '%Y-%m-%d').date()
        except ValueError as exc:
            raise CommandError(f'Неверный формат даты: {exc}') from exc

        if start_date > end_date:
            raise CommandError('--start должна быть <= --end')

        window_hours = int(options['window_hours'])
        if window_hours <= 0:
            raise CommandError('--window-hours должен быть > 0')

        self.stdout.write(
            self.style.NOTICE(
                f'Предрасчет кэша location-presence: {start_date} → {end_date}, window={window_hours}h, sync={options["sync"]}'
            )
        )

        service = LocationPresenceAnalyticsService()
        result = service.calculate(
            start_date=start_date,
            end_date=end_date,
            window_hours=window_hours,
            auto_sync=bool(options['sync']),
        )

        LocationPresenceStatsCache.objects.update_or_create(
            start_date=start_date,
            end_date=end_date,
            window_hours=window_hours,
            defaults={'payload': result},
        )

        self.stdout.write(self.style.SUCCESS('Кэш обновлен успешно'))
        self.stdout.write(str(result))
