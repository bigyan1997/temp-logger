from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('setup', '0008_supplier_usually_frozen'),
    ]

    operations = [
        migrations.RenameField(model_name='staffmember', old_name='can_sign_off', new_name='both_logins'),
        migrations.AlterField(
            model_name='staffmember',
            name='both_logins',
            field=models.BooleanField(default=False, help_text='Offered on the day login as well as the night login.'),
        ),
    ]
