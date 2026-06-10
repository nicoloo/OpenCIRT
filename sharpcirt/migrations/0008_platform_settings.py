from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0007_incident_ai_rephrase_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ai_provider', models.CharField(
                    choices=[('NONE', 'Disabled'), ('ANTHROPIC', 'Anthropic (Claude)'), ('OPENAI', 'OpenAI (GPT)')],
                    default='NONE',
                    max_length=20,
                )),
                ('ai_api_key', models.CharField(blank=True, default='', max_length=512)),
            ],
            options={'verbose_name': 'Platform Settings'},
        ),
    ]
