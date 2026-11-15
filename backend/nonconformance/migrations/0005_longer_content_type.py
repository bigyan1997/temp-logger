from django.db import migrations, models


class Migration(migrations.Migration):
    """Word, Excel and PowerPoint files have long content types, so the column that holds it is made longer."""

    dependencies = [
        ('nonconformance', '0004_allow_delete'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photo',
            name='content_type',
            field=models.CharField(max_length=100),
        ),
    ]
