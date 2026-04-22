from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amplitude', '0013_allowedemployeepageaccess'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='DROP TABLE IF EXISTS amplitude_allowedemployeeposition CASCADE;',
                    reverse_sql=(
                        "CREATE TABLE IF NOT EXISTS amplitude_allowedemployeeposition ("
                        "id bigserial PRIMARY KEY, "
                        "position_guid varchar(64) NOT NULL UNIQUE, "
                        "is_active boolean NOT NULL DEFAULT true, "
                        "note varchar(255) NOT NULL DEFAULT '', "
                        "created_at timestamp with time zone NOT NULL, "
                        "updated_at timestamp with time zone NOT NULL"
                        ");"
                    ),
                ),
            ],
            state_operations=[
                migrations.DeleteModel(
                    name='AllowedEmployeePosition',
                ),
            ],
        ),
    ]
