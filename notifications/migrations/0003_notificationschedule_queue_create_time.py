from django.db import migrations, models


def copy_send_time_to_queue_create_time(apps, schema_editor):
    NotificationSchedule = apps.get_model('notifications', 'NotificationSchedule')
    for schedule in NotificationSchedule.objects.filter(queue_create_time__isnull=True):
        schedule.queue_create_time = schedule.send_time
        schedule.save(update_fields=['queue_create_time'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_notificationschedule_tracking_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationschedule',
            name='queue_create_time',
            field=models.TimeField(blank=True, null=True, verbose_name='Время создания очереди (Asia/Almaty)'),
        ),
        migrations.RunPython(copy_send_time_to_queue_create_time, noop_reverse),
    ]
