from django.db import migrations

# Same protection as the readings: Postgres refuses to delete these rows (the function is made in audit 0002).
NEVER_DELETE = ['nonconformance_nonconformance', 'nonconformance_update', 'nonconformance_photo']


def add_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return  # the quick SQLite test mode has no triggers
    for table in NEVER_DELETE:
        schema_editor.execute(
            f'CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} '
            'FOR EACH ROW EXECUTE FUNCTION refuse_record_change();'
        )


def remove_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for table in NEVER_DELETE:
        schema_editor.execute(f'DROP TRIGGER IF EXISTS {table}_no_delete ON {table};')


class Migration(migrations.Migration):
    dependencies = [
        ('audit', '0002_protect_records'),
        ('nonconformance', '0001_nonconformance'),
    ]

    operations = [migrations.RunPython(add_triggers, remove_triggers)]
