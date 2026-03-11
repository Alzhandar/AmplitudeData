from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amplitude', '0011_locationpresencestatscache'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='mobilesession',
            name='raw_event',
        ),
    ]
