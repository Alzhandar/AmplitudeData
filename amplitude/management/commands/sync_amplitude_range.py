from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from amplitude.services.sync_service import AmplitudeSyncService


class Command(BaseCommand):
    help = 'Синхронизировать события Amplitude за указанный диапазон дат'

    def add_arguments(self, parser):
        parser.add_argument('--start', required=True, help='Начальная дата YYYY-MM-DD')
        parser.add_argument('--end', required=True, help='Конечная дата YYYY-MM-DD')

    def handle(self, *args, **options):
        try:
            start_date = datetime.strptime(options['start'], '%Y-%m-%d').date()
            end_date = datetime.strptime(options['end'], '%Y-%m-%d').date()
        except ValueError as exc:
            raise CommandError(f'Неверный формат даты: {exc}') from exc

        if start_date > end_date:
            raise CommandError('--start должна быть <= --end')

        self.stdout.write(
            self.style.NOTICE(f'Запуск синхронизации: {start_date} → {end_date}')
        )

        service = AmplitudeSyncService()
        result = service.sync_date_range(start_date=start_date, end_date=end_date)

        for day in result['days']:
            self.stdout.write(
                f"  {day['date']}: обработано={day['processed']}, вставлено={day['inserted']}"
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nИтого: обработано={result['total_processed']}, вставлено={result['total_inserted']}"
        ))
