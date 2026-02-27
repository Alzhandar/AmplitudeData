from datetime import time

from django.db import models


class MobileSession(models.Model):
    date = models.DateField(db_index=True, verbose_name='Дата')
    event_time = models.DateTimeField(db_index=True, verbose_name='Время события')
    event_type = models.CharField(max_length=255, blank=True, verbose_name='Тип события')
    user_id = models.CharField(max_length=255, blank=True, verbose_name='ID пользователя')
    device_id = models.CharField(max_length=255, db_index=True, verbose_name='ID устройства')
    phone_number = models.CharField(max_length=64, blank=True, verbose_name='Номер телефона')
    platform = models.CharField(max_length=64, blank=True, verbose_name='Платформа')
    insert_id = models.CharField(max_length=255, blank=True, verbose_name='Insert ID')
    dedupe_key = models.CharField(max_length=64, unique=True, verbose_name='Ключ дедупликации')
    raw_event = models.JSONField(default=dict, blank=True, verbose_name='Сырое событие')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        ordering = ('-event_time',)
        verbose_name = 'Сессия мобильного события'
        verbose_name_plural = 'Сессии мобильных событий'


class DailyDeviceActivity(models.Model):
    date = models.DateField(db_index=True, verbose_name='Дата')
    user_id = models.CharField(max_length=255, blank=True, verbose_name='ID пользователя')
    device_id = models.CharField(max_length=255, db_index=True, verbose_name='ID устройства')
    phone_number = models.CharField(max_length=64, blank=True, verbose_name='Номер телефона')
    platform = models.CharField(max_length=64, blank=True, verbose_name='Платформа')
    visits_count = models.PositiveIntegerField(default=0, verbose_name='Количество визитов')
    first_seen = models.DateTimeField(null=True, blank=True, verbose_name='Первый визит')
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name='Последний визит')
    visit_times = models.JSONField(default=list, blank=True, verbose_name='Времена визитов')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('date', 'device_id'), name='uniq_daily_activity_per_device'),
        ]
        ordering = ('-last_seen',)
        verbose_name = 'Дневная активность устройства'
        verbose_name_plural = 'Дневная активность устройств'


class AmplitudeSyncSchedule(models.Model):
    run_at = models.TimeField(default=time(1, 0), verbose_name='Время запуска')
    enabled = models.BooleanField(default=True, verbose_name='Включено')
    last_run_on = models.DateField(null=True, blank=True, verbose_name='Последний запуск (дата)')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Amplitude Sync Schedule'
        verbose_name_plural = 'Amplitude Sync Schedules'

    def __str__(self) -> str:
        return f'Sync at {self.run_at.strftime("%H:%M")} (enabled={self.enabled})'
