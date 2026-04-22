from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('amplitude', '0012_remove_mobilesession_raw_event'),
    ]

    operations = [
        migrations.CreateModel(
            name='AllowedEmployeePageAccess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'page',
                    models.CharField(
                        choices=[
                            ('analytics', 'Аналитика'),
                            ('bonus-transactions', 'Транзакция бонусов'),
                            ('coupon-dispatch', 'Отправка купонов'),
                            ('push-dispatch', 'Отправка пушей'),
                            ('blacklist', 'Черный список'),
                        ],
                        db_index=True,
                        max_length=64,
                        verbose_name='Раздел портала',
                    ),
                ),
                ('position_guid', models.CharField(db_index=True, max_length=64, verbose_name='GUID позиции')),
                ('is_active', models.BooleanField(default=True, verbose_name='Доступ активен')),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='Комментарий')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Доступ к разделу по позиции',
                'verbose_name_plural': 'Доступы к разделам по позициям',
                'ordering': ('page', 'position_guid'),
                'constraints': [
                    models.UniqueConstraint(fields=('page', 'position_guid'), name='uniq_allowed_employee_page_access')
                ],
            },
        ),
    ]
