from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0003_add_campaign_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='incident',
            name='resolution',
            field=models.CharField(
                max_length=30,
                blank=True,
                default='',
                choices=[
                    ('TRUE_POSITIVE',    'True Positive'),
                    ('FALSE_POSITIVE',   'False Positive'),
                    ('SECURITY_TESTING', 'Security Testing'),
                    ('AUTHORIZED_SCAN',  'Authorized Scan'),
                    ('DUPLICATE',        'Duplicate'),
                    ('INFORMATIONAL',    'Informational'),
                    ('UNDETERMINED',     'Undetermined'),
                ],
            ),
        ),
        migrations.AddField(
            model_name='incident',
            name='resolution_note',
            field=models.TextField(blank=True, default=''),
        ),
    ]
