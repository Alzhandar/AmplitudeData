from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_story_recipient_config_and_drop_story_templates'),
    ]

    operations = [
        migrations.AddField(
            model_name='storyrecipientconfig',
            name='story_date',
            field=models.DateField(blank=True, db_index=True, null=True, verbose_name='Дата Story (Asia/Almaty)'),
        ),
    ]
