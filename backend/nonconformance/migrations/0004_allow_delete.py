from django.db import migrations

# Owner's decision (2026-11-12): a non-conformance report may be deleted from the app (with a reason, and an audit line that
# keeps what was deleted). So Postgres no longer refuses DELETE on these three tables. Voiding still works as before.
TABLES = ['nonconformance_nonconformance', 'nonconformance_update', 'nonconformance_photo']


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
    dependencies = [('nonconformance', '0003_photo_update')]

    operations = [migrations.RunPython(drop_triggers, add_triggers)]
