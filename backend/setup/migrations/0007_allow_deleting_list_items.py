from django.db import migrations

# The lists an admin may now delete from (when nothing uses the item). Readings, corrective actions and the
# audit log stay protected by audit migration 0002.
LIST_TABLES = [
    'setup_staffmember',
    'setup_unit',
    'setup_supplier',
    'setup_run',
    'setup_alertrecipient',
    'accounts_user',
]


def drop_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return  # the quick SQLite test mode has no triggers
    for table in LIST_TABLES:
        schema_editor.execute(f'DROP TRIGGER IF EXISTS {table}_no_delete ON {table};')


def restore_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for table in LIST_TABLES:
        schema_editor.execute(
            f'CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} '
            'FOR EACH ROW EXECUTE FUNCTION refuse_record_change();'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('setup', '0006_alertrecipient'),
        ('accounts', '0001_initial'),
        ('audit', '0002_protect_records'),
    ]

    operations = [migrations.RunPython(drop_triggers, restore_triggers)]
