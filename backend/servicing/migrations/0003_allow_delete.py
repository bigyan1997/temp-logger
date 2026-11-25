from django.db import migrations

# Service records may now be deleted (owner, 2026-11-25), so Postgres stops blocking it, and voiding is gone.
TABLES = ['servicing_servicerecord', 'servicing_servicefile']


def drop_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for table in TABLES:
        schema_editor.execute(f'DROP TRIGGER IF EXISTS {table}_no_delete ON {table};')


def add_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for table in TABLES:
        schema_editor.execute(
            f'CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} '
            'FOR EACH ROW EXECUTE FUNCTION refuse_record_change();'
        )


class Migration(migrations.Migration):
    dependencies = [('servicing', '0002_never_delete')]

    operations = [
        migrations.RunPython(drop_triggers, add_triggers),
        migrations.RemoveField(model_name='servicerecord', name='voided'),
        migrations.RemoveField(model_name='servicerecord', name='void_reason'),
        migrations.RemoveField(model_name='servicefile', name='voided'),
        migrations.RemoveField(model_name='servicefile', name='void_reason'),
    ]
