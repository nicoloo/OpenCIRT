from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0005_alter_campaign_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='platform_role',
            field=models.CharField(
                max_length=15,
                blank=True,
                default='',
                choices=[
                    ('',            'None'),
                    ('SOC_ANALYST', 'SOC Analyst'),
                    ('SOC_LEAD',    'SOC Lead'),
                ],
            ),
        ),
    ]
