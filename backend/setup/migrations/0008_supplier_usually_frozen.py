from django.db import migrations, models

# Suppliers that deliver frozen product (matched on a word in the name, as seeded in 0003).
FROZEN_SUPPLIERS = ['Quality', 'Garlos', 'Helen', 'Knefeh']


def mark_frozen_suppliers(apps, schema_editor):
    Supplier = apps.get_model('setup', 'Supplier')
    for word in FROZEN_SUPPLIERS:
        Supplier.objects.filter(name__icontains=word).update(usually_frozen=True)


class Migration(migrations.Migration):
    dependencies = [
        ('setup', '0007_allow_deleting_list_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplier',
            name='usually_frozen',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_frozen_suppliers, migrations.RunPython.noop),
    ]
