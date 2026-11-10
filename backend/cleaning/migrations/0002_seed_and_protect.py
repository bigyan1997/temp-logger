from django.db import migrations

# The columns of the paper Table 8 (HACCP Plan 1.6), in order. The paper has no frequency for Clean Shelving,
# so it starts as daily; the admin can change it on the Tasks page.
TASKS = [
    ('Bathroom check (toilet paper, hand towel, soap)', 'daily'),
    ('Warehouse clean - front', 'daily'),
    ('Warehouse clean - back', 'daily'),
    ('Repack sink - water/soap check', 'daily'),
    ('Van clean #6', 'daily'),
    ('Van clean #7', 'daily'),
    ('Van clean #8', 'daily'),
    ('Van clean #4', 'daily'),
    ('Stock put away', 'daily'),
    ('Forklift recharge & water (1st of month)', 'monthly'),
    ('Clean shelving', 'daily'),
    ('Pest spray (quarterly)', 'quarterly'),
    ('Bait change (quarterly)', 'quarterly'),
]


def add_tasks(apps, schema_editor):
    CleaningTask = apps.get_model('cleaning', 'CleaningTask')
    for name, frequency in TASKS:
        CleaningTask.objects.get_or_create(name=name, defaults={'frequency': frequency})


def add_trigger(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return  # the quick SQLite test mode has no triggers
    # Ticks are records: Postgres refuses to delete them (the function is made in audit 0002).
    schema_editor.execute(
        'CREATE TRIGGER cleaning_cleaningcheck_no_delete BEFORE DELETE ON cleaning_cleaningcheck '
        'FOR EACH ROW EXECUTE FUNCTION refuse_record_change();'
    )


def remove_trigger(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute('DROP TRIGGER IF EXISTS cleaning_cleaningcheck_no_delete ON cleaning_cleaningcheck;')


class Migration(migrations.Migration):
    dependencies = [
        ('audit', '0002_protect_records'),
        ('cleaning', '0001_cleaning'),
    ]

    operations = [
        migrations.RunPython(add_tasks, migrations.RunPython.noop),
        migrations.RunPython(add_trigger, remove_trigger),
    ]
