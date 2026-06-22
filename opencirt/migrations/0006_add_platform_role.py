import os
from django.db import migrations, models
from django.core.management import call_command


def load_demo_incidents(apps, schema_editor):
    if os.environ.get('LOAD_DEMO_DATA', '').lower() != 'true':
        return
    fixture_path = os.path.join(os.path.dirname(__file__), '../fixtures/incidents_demo.json')
    if os.path.exists(fixture_path):
        call_command('loaddata', fixture_path, verbosity=0)


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
        migrations.RunPython(
            code=load_demo_incidents,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
