from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0014_seed_default_admin'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='title',
            field=models.CharField(default='', max_length=200),
        ),
    ]
