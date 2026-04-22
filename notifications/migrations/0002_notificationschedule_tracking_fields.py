from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationschedule',
            name='last_checked_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Последняя проверка очереди'),
        ),
        migrations.AddField(
            model_name='notificationschedule',
            name='last_queue_entry_created_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Последнее создание записи очереди'),
        ),
    ]
