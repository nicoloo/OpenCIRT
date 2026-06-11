from django.db import migrations


class Migration(migrations.Migration):
    """Merge the auto-generated reputation migration with reputation_score."""

    dependencies = [
        ('opencirt', '0002_genericioc_reputation'),
        ('opencirt', '0009_genericioc_reputation_score'),
    ]

    operations = []
