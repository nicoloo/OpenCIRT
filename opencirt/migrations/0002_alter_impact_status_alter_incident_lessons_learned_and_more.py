import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='impact',
            name='status',
            field=models.CharField(
                choices=[
                    ('CONTINUOUS', 'Continuous'),
                    ('IN_PROGRESS', 'In Progress'),
                    ('RESOLVED', 'Resolved'),
                    ('CLOSED', 'Closed'),
                ],
                default='IN_PROGRESS',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='incident',
            name='lessons_learned',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='incident',
            name='technical_details',
            field=models.TextField(default=''),
        ),
    ]
