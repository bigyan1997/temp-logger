from django.db import migrations

# (name, kind, max temperature in C, display order)
UNITS = [
    ('Coolroom', 'chilled', '5.0', 1),
    ('Old Coolroom', 'chilled', '5.0', 2),
    ('Freezer', 'frozen', '-15.0', 3),
    ('Chest Freezer', 'frozen', '-15.0', 4),
]

SUPPLIERS = [
    'Atown - Knefeh only',
    'Posh Foods',
    "Shepherd's - Pies/Rolls only",
    'Yianni Fine Food - Lasagne/Moussaka only',
    'Madhouse - Pies only',
    'Helens Fine Foods',
    'Garlos Pies',
    'Quality Patisserie',
]

RUNS = ['A', 'B', 'C', 'D', 'E', 'G', 'H', 'J', 'K', 'L', 'M']  # there is no F or I


def seed_defaults(apps, schema_editor):
    Unit = apps.get_model('setup', 'Unit')
    Supplier = apps.get_model('setup', 'Supplier')
    Run = apps.get_model('setup', 'Run')

    for name, kind, max_temp, order in UNITS:
        Unit.objects.get_or_create(
            name=name, defaults={'kind': kind, 'max_temp': max_temp, 'sort_order': order}
        )
    for name in SUPPLIERS:
        Supplier.objects.get_or_create(name=name)
    for code in RUNS:
        Run.objects.get_or_create(code=code)


class Migration(migrations.Migration):
    dependencies = [('setup', '0002_units_suppliers_runs')]

    # Records are never deleted, so there is nothing to undo.
    operations = [migrations.RunPython(seed_defaults, migrations.RunPython.noop)]
