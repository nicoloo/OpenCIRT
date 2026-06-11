from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='genericioc',
            name='reputation',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
