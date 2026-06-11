from django.db import migrations, models
from django.core.management import call_command
import os


def load_demo_incidents(apps, schema_editor):
    fixture_path = os.path.join(os.path.dirname(__file__), '../fixtures/incidents_demo.json')
    if os.path.exists(fixture_path):
        call_command('loaddata', fixture_path, verbosity=0)


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0015_alter_action_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='incident',
            name='external_reference',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.RunPython(load_demo_incidents, migrations.RunPython.noop),
    ]
