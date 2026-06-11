from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0012_alter_genericioc_type_alter_platformsettings_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='CtiProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(
                    choices=[
                        ('VIRUSTOTAL',    'VirusTotal'),
                        ('ABUSEIPDB',     'AbuseIPDB'),
                        ('SHODAN',        'Shodan'),
                        ('OTXALIENVAULT', 'OTX AlienVault'),
                        ('MISP',          'MISP'),
                    ],
                    max_length=30,
                    unique=True,
                )),
                ('api_key',  models.CharField(blank=True, default='', max_length=512)),
                ('base_url', models.CharField(
                    blank=True, default='', max_length=255,
                    help_text='Required for self-hosted sources (e.g. MISP).',
                )),
                ('enabled', models.BooleanField(default=True)),
            ],
        ),
    ]
