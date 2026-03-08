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

## Production (Nginx + SSL)

### 1) Prepare env

Use `.env` (or copy from `.env.example`) and set at minimum:

- `DEBUG=False`
- `ALLOWED_HOSTS=your-domain.com`
- `CSRF_TRUSTED_ORIGINS=https://your-domain.com`
- `SSL_DOMAIN=your-domain.com`
- `SSL_EMAIL=you@your-domain.com`
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECURE_HSTS_SECONDS=31536000`

### 2) Start production stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 3) Issue first Let's Encrypt certificate

```bash
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
	--webroot -w /var/www/certbot \
	-d "$SSL_DOMAIN" \
	--email "$SSL_EMAIL" \
	--agree-tos --no-eff-email
```

### 4) Reload nginx with HTTPS config

```bash
docker compose -f docker-compose.prod.yml restart nginx
```

Notes:

- `web` runs with `gunicorn` in production mode (`entrypoint.sh web-prod`).
- `certbot` container runs auto-renew every 12h.
- `nginx` serves `/static/` directly and proxies app requests to Django.

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

## Frontend (Next.js)

- See frontend integration documentation: `docs/FRONTEND_NEXTJS.md`
