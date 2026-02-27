# AmplitudeData

## Stack

- Django + PostgreSQL
- Celery + Redis
- Docker Compose

## Environment

Copy `.env.example` to `.env` and set:

- `AMPLITUDE_API_KEY`
- `AMPLITUDE_SECRET_KEY`
- `AMPLITUDE_EXPORT_URL` (default: `https://amplitude.com/api/2/export`)
- `AMPLITUDE_MOBILE_EVENT_TYPES` (optional CSV filter by event names)

## Run

```bash
docker compose up --build
```

## Amplitude sync

- Celery scheduler task: `amplitude.tasks.run_scheduled_sync`
- Time is configured in Django admin: `Amplitude Sync Schedules` (`run_at`, `enabled`)
- Beat checks schedule every minute and runs sync once per day at configured time

## API

- `GET /api/amplitude/today-mobile-activity/`
- Implemented with DRF ViewSet (supports optional `?date=YYYY-MM-DD`)

Returns aggregated records for the current day:

- `device_id`
- `phone_number`
- list of visit times (`visit_times`)
- `first_seen`, `last_seen`, `visits_count`
