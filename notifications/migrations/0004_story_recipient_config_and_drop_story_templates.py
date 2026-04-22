from django.db import migrations, models


def clear_story_template_data(apps, schema_editor):
    StoryDisplayTemplate = apps.get_model('notifications', 'StoryDisplayTemplate')
    StoryTemplate = apps.get_model('notifications', 'StoryTemplate')

    StoryDisplayTemplate.objects.all().delete()
    StoryTemplate.objects.all().delete()


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('notifications', '0003_notificationschedule_queue_create_time'),
    ]

    operations = [
        migrations.RunPython(clear_story_template_data, migrations.RunPython.noop),
        migrations.DeleteModel(
            name='StoryDisplayTemplate',
        ),
        migrations.DeleteModel(
            name='StoryTemplate',
        ),
        migrations.CreateModel(
            name='StoryRecipientConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('hb_kids', 'HB Kids')], max_length=32, unique=True, verbose_name='Тип уведомления')),
                ('story_id', models.PositiveBigIntegerField(db_index=True, verbose_name='ID готового Story во внешнем API')),
                ('enabled', models.BooleanField(default=True, verbose_name='Включен')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Настройка Story получателя',
                'verbose_name_plural': 'Настройки Story получателей',
                'ordering': ('notification_type',),
            },
        ),
    ]
