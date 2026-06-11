from django.db import migrations, models
from django.core.management import call_command
import os


def load_demo_incidents(apps, schema_editor):
    """Load demo incident fixture data (runs after Action.title is widened)."""
    fixture_path = os.path.join(os.path.dirname(__file__), '../fixtures/incidents_demo.json')
    if os.path.exists(fixture_path):
        call_command('loaddata', fixture_path, verbosity=0)


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
        migrations.RunPython(load_demo_incidents, migrations.RunPython.noop),
    ]
