import django.db.models.functions.text
from django.db import migrations, models

TABLE = 'setup_alertrecipient'


def add_trigger(apps, schema_editor):
    """Like the other lists, addresses are never deleted (the function comes from audit 0002)."""
    if schema_editor.connection.vendor != 'postgresql':
        return  # the quick SQLite test mode has no triggers
    schema_editor.execute(
        f'CREATE TRIGGER {TABLE}_no_delete BEFORE DELETE ON {TABLE} '
        'FOR EACH ROW EXECUTE FUNCTION refuse_record_change();'
    )


def remove_trigger(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(f'DROP TRIGGER IF EXISTS {TABLE}_no_delete ON {TABLE};')


class Migration(migrations.Migration):

    dependencies = [
        ('setup', '0005_sign_off_managers'),
        ('audit', '0002_protect_records'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlertRecipient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['email'],
                'constraints': [models.UniqueConstraint(django.db.models.functions.text.Lower('email'), name='alertrecipient_email_ci_unique')],
            },
        ),
        migrations.RunPython(add_trigger, remove_trigger),
    ]
