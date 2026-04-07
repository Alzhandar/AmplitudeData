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

        def on_day_done(day_result: dict) -> None:
            day = day_result['date']
            if day_result.get('error'):
                self.stdout.write(
                    self.style.ERROR(
                        f"День {day} завершен с ошибкой: {day_result['error']}"
                    )
                )
                return

            self.stdout.write(
                self.style.SUCCESS(
                    f"День {day} завершен: обработано={day_result['processed']}, вставлено={day_result['inserted']}"
                )
            )

        result = service.sync_date_range(
            start_date=start_date,
            end_date=end_date,
            progress_callback=on_day_done,
        )

        for day in result['days']:
            if day.get('error'):
                self.stdout.write(
                    self.style.ERROR(f"  {day['date']}: ОШИБКА — {day['error']}")
                )
            else:
                self.stdout.write(
                    f"  {day['date']}: обработано={day['processed']}, вставлено={day['inserted']}"
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nИтого: обработано={result['total_processed']}, вставлено={result['total_inserted']}"
        ))
