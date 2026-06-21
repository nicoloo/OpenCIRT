from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0004_add_resolution_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campaign',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
