from django.db import migrations


class Migration(migrations.Migration):
    """Remove the reputation_score column superseded by reputation."""

    dependencies = [
        ('opencirt', '0010_merge_reputation_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='genericioc',
            name='reputation_score',
        ),
    ]
