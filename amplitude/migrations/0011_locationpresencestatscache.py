from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('amplitude', '0010_useremployeebinding'),
    ]

    operations = [
        migrations.CreateModel(
            name='LocationPresenceStatsCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(db_index=True, verbose_name='Начальная дата')),
                ('end_date', models.DateField(db_index=True, verbose_name='Конечная дата')),
                ('window_hours', models.PositiveIntegerField(db_index=True, default=24, verbose_name='Окно, часы')),
                ('payload', models.JSONField(blank=True, default=dict, verbose_name='Результат расчета')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Кэш статистики присутствия',
                'verbose_name_plural': 'Кэш статистики присутствия',
                'ordering': ('-updated_at',),
            },
        ),
        migrations.AddConstraint(
            model_name='locationpresencestatscache',
            constraint=models.UniqueConstraint(fields=('start_date', 'end_date', 'window_hours'), name='uniq_location_presence_stats_cache_key'),
        ),
    ]
