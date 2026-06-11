from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0004_add_shared_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='incident',
            name='tlp',
            field=models.CharField(
                choices=[('CLEAR', 'CLEAR'), ('GREEN', 'GREEN'), ('AMBER', 'AMBER'), ('RED', 'RED')],
                default='CLEAR',
                max_length=10,
            ),
        ),
    ]
