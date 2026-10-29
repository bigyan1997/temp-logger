from django.db import migrations

# Tables whose rows must never be deleted.
NEVER_DELETE = [
    'readings_storagereading',
    'readings_receivingcheck',
    'readings_dispatchreading',
    'readings_correctiveaction',
    'setup_staffmember',
    'setup_unit',
    'setup_supplier',
    'setup_run',
    'accounts_user',
    'audit_auditlog',
]
# Tables whose rows must never be changed either.
NEVER_CHANGE = ['audit_auditlog']

CREATE_FUNCTION = """
CREATE OR REPLACE FUNCTION refuse_record_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Records are never % (table %). Void or deactivate instead.', lower(TG_OP), TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;
"""


def add_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return  # the quick SQLite test mode has no triggers
    schema_editor.execute(CREATE_FUNCTION, params=None)  # params=None: the SQL contains literal % signs
    for table in NEVER_DELETE:
        schema_editor.execute(
            f'CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} '
            'FOR EACH ROW EXECUTE FUNCTION refuse_record_change();'
        )
    for table in NEVER_CHANGE:
        schema_editor.execute(
            f'CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table} '
            'FOR EACH ROW EXECUTE FUNCTION refuse_record_change();'
        )


def remove_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for table in NEVER_DELETE:
        schema_editor.execute(f'DROP TRIGGER IF EXISTS {table}_no_delete ON {table};')
    for table in NEVER_CHANGE:
        schema_editor.execute(f'DROP TRIGGER IF EXISTS {table}_no_update ON {table};')
    schema_editor.execute('DROP FUNCTION IF EXISTS refuse_record_change();')


class Migration(migrations.Migration):
    dependencies = [
        ('audit', '0001_initial'),
        ('accounts', '0001_initial'),
        ('setup', '0003_seed_defaults'),
        ('readings', '0001_initial'),
    ]

    operations = [migrations.RunPython(add_triggers, remove_triggers)]
