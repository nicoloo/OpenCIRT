import os
import secrets

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.db import migrations, models


DEFAULT_CATEGORIES = [
    ('Malware',                    '#ef4444'),
    ('Ransomware',                 '#dc2626'),
    ('Phishing',                   '#f97316'),
    ('Data Breach',                '#8b5cf6'),
    ('Insider Threat',             '#b91c1c'),
    ('Fraud',                      '#d97706'),
    ('DDoS',                       '#3b82f6'),
    ('Supply Chain Attack',        '#10b981'),
    ('Social Engineering',         '#f59e0b'),
    ('Vulnerability Exploitation', '#06b6d4'),
    ('APT',                        '#7c3aed'),
    ('Unauthorized Access',        '#6b7280'),
]


def seed_incident_categories(apps, schema_editor):
    IncidentCategory = apps.get_model('opencirt', 'IncidentCategory')
    for name, color in DEFAULT_CATEGORIES:
        IncidentCategory.objects.get_or_create(name=name, defaults={'color': color})


def seed_default_admin(apps, schema_editor):
    User = apps.get_model('opencirt', 'User')
    User.objects.filter(username='lead_admin').delete()

    initial_password = secrets.token_urlsafe(16)
    _, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@opencirt.local',
            'displayname': 'Admin',
            'is_admin': True,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
            'password': make_password(initial_password),
        },
    )
    if created:
        print(f'\n\033[93m*** OpenCIRT initial admin password: {initial_password} ***\033[0m')
        print('\033[93m*** Change it immediately after first login. ***\033[0m\n')


def load_demo_incidents(apps, schema_editor):
    if os.environ.get('LOAD_DEMO_DATA', '').lower() != 'true':
        return
    fixture_path = os.path.join(os.path.dirname(__file__), '../fixtures/incidents_demo.json')
    if os.path.exists(fixture_path):
        call_command('loaddata', fixture_path, verbosity=0)


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='IncidentCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('color', models.CharField(default='#796FA7', max_length=7)),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('is_admin', models.BooleanField(default=False)),
                ('first_connection_time', models.DateTimeField(auto_now_add=True)),
                ('last_connection_time', models.DateTimeField(blank=True, null=True)),
                ('displayname', models.CharField(blank=True, max_length=100, null=True)),
                ('profile_picture', models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics/')),
                ('light_mode', models.CharField(default='light_mode', max_length=15)),
                ('preferences', models.JSONField(blank=True, default=dict)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to.', related_name='custom_user_groups', to='auth.group')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='custom_user_permissions', to='auth.permission')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Incident',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('OPEN', 'Open'), ('IN_PROGRESS', 'In Progress'), ('RESOLVED', 'Resolved'), ('CLOSED', 'Closed')], default='OPEN', max_length=20)),
                ('severity', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')], default='MEDIUM', max_length=10)),
                ('executive_summary', models.TextField()),
                ('lessons_learned', models.TextField(default='SOME STRING')),
                ('technical_details', models.TextField(default='SOME STRING')),
                ('external_reference', models.CharField(blank=True, default='', max_length=255)),
                ('export_include_timeline', models.BooleanField(default=True)),
                ('export_include_iocs', models.BooleanField(default=True)),
                ('export_include_attachements', models.BooleanField(default=True)),
                ('starting_time', models.DateTimeField()),
                ('ending_time', models.DateTimeField()),
                ('duration', models.DurationField()),
                ('time_to_detect', models.DurationField()),
                ('time_to_respond', models.DurationField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_public', models.BooleanField(default=False)),
                ('iocs_shared', models.BooleanField(default=False)),
                ('invite_code', models.CharField(blank=True, default='', max_length=6)),
                ('tlp', models.CharField(choices=[('CLEAR', 'CLEAR'), ('GREEN', 'GREEN'), ('AMBER', 'AMBER'), ('RED', 'RED')], default='CLEAR', max_length=10)),
                ('ai_rephrase_enabled', models.BooleanField(default=False)),
                ('categories', models.ManyToManyField(blank=True, related_name='incidents', to='opencirt.incidentcategory')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='incident_created', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(default='', max_length=30)),
                ('color', models.CharField(default='#000000', max_length=7)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tags_created', to=settings.AUTH_USER_MODEL)),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', to='opencirt.incident')),
            ],
        ),
        migrations.CreateModel(
            name='GenericIoc',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tag', models.TextField()),
                ('status', models.CharField(choices=[('COMPROMISED', 'Compromised'), ('POTENTIALLY_COMPROMISED', 'Potentially Compromised'), ('SAFE', 'Safe')], default='SAFE', max_length=30)),
                ('description', models.TextField()),
                ('value', models.TextField()),
                ('type', models.CharField(choices=[('IPADRESS', 'IP Address'), ('URL', 'URL'), ('DOMAIN', 'Domain'), ('NETWORK', 'Network / CIDR'), ('EMAIL', 'Email'), ('HASH', 'Hash'), ('FILE', 'File'), ('FILENAME', 'Filename'), ('ACCOUNT', 'Account'), ('PASSWORD', 'Password'), ('FOLDER', 'Folder'), ('SRC_PORT', 'Source Port'), ('DST_PORT', 'Destination Port'), ('DEVICE', 'Device'), ('ISP', 'Isp'), ('PERSON', 'Person'), ('OTHER', 'Other')], default='OTHER', max_length=20)),
                ('reputation', models.JSONField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='genericioc_created', to=settings.AUTH_USER_MODEL)),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='genericiocs', to='opencirt.incident')),
                ('tags', models.ManyToManyField(related_name='ioc_tags', to='opencirt.tag')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('observed_at', models.DateTimeField(null=True)),
                ('starting_time', models.DateTimeField(null=True)),
                ('ending_time', models.DateTimeField(null=True)),
                ('title', models.CharField(default='', max_length=200)),
                ('description', models.TextField(default='')),
                ('type', models.CharField(choices=[('MALICIOUS', 'Malicious'), ('DEFENSIVE', 'Defensive'), ('MITIGATION', 'Mitigation'), ('COMMUNICATION', 'Communication'), ('ALERT', 'Alert'), ('OTHER', 'Other')], default='OTHER', max_length=20)),
                ('is_first_action_this_day', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='actions_created', to=settings.AUTH_USER_MODEL)),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='actions', to='opencirt.incident')),
                ('iocs', models.ManyToManyField(related_name='actions', to='opencirt.genericioc')),
                ('tags', models.ManyToManyField(related_name='action_tags', to='opencirt.tag')),
            ],
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('INCIDENT_LEAD', 'Incident Lead'), ('RESPONDER', 'Responder'), ('READER', 'Reader')], max_length=20)),
                ('display_role', models.CharField(default='', max_length=30)),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incident_roles', to='opencirt.incident')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_roles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'incident')},
            },
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=50)),
                ('text', models.TextField()),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='note_created', to=settings.AUTH_USER_MODEL)),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='opencirt.incident')),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=50)),
                ('external_reference', models.CharField(max_length=50)),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('OPEN', 'Open'), ('IN_PROGRESS', 'In Progress'), ('DONE', 'Done')], default='OPEN', max_length=20)),
                ('priority', models.CharField(choices=[('URGENT', 'Urgent'), ('HIGH', 'High'), ('MEDIUM', 'Medium'), ('LOW', 'Low')], default='MEDIUM', max_length=20)),
                ('assignee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='task_assignee', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='task_created', to=settings.AUTH_USER_MODEL)),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='opencirt.incident')),
                ('tags', models.ManyToManyField(related_name='tags_task', to='opencirt.tag')),
            ],
        ),
        migrations.CreateModel(
            name='Impact',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=50)),
                ('external_reference', models.CharField(max_length=50)),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('CONTINUOUS', 'Continuous'), ('IN_PROGRESS', 'In Progress'), ('RESOLVED', 'Resolved'), ('CLOSED', 'Closed')], default='OPEN', max_length=20)),
                ('severity', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')], default='MEDIUM', max_length=20)),
                ('type', models.CharField(choices=[('BUSINESS_IMPACT', 'Business impact'), ('REPUTATION', 'Reputation'), ('DATA_LOSS', 'Data Loss'), ('SYSTEMS_AVAILABILITY', 'Systems availability'), ('NOT_DEFINED', 'Not defined')], default='N/A', max_length=20)),
                ('starting_time', models.DateTimeField(null=True)),
                ('ending_time', models.DateTimeField(null=True)),
                ('duration', models.DurationField(null=True)),
                ('action', models.ManyToManyField(related_name='impacts', to='opencirt.action')),
                ('assignee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='impact_assignee', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='impact_created', to=settings.AUTH_USER_MODEL)),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='impacts', to='opencirt.incident')),
                ('tags', models.ManyToManyField(related_name='tags_impact', to='opencirt.tag')),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('text', models.TextField()),
                ('is_bot', models.BooleanField(default=False)),
                ('link', models.CharField(blank=True, max_length=255, null=True)),
                ('incident', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='opencirt.incident')),
                ('sender', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages_sent', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SharedFile',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('file', models.FileField(upload_to='incident_files/')),
                ('original_name', models.CharField(max_length=255)),
                ('size', models.PositiveIntegerField(default=0)),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_files', to='opencirt.incident')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_files', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.CharField(blank=True, default='', max_length=45)),
                ('action', models.CharField(choices=[('CREATE', 'Create'), ('UPDATE', 'Update'), ('DELETE', 'Delete'), ('EXPORT', 'Export'), ('ACCESS', 'Access')], max_length=10)),
                ('object_type', models.CharField(max_length=50)),
                ('description', models.TextField()),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='opencirt.incident')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='PlatformSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ai_provider', models.CharField(choices=[('NONE', 'Disabled'), ('ANTHROPIC', 'Anthropic (Claude)'), ('OPENAI', 'OpenAI (GPT)')], default='NONE', max_length=20)),
                ('ai_api_key', models.CharField(blank=True, default='', max_length=512)),
            ],
            options={
                'verbose_name': 'Platform Settings',
            },
        ),
        migrations.CreateModel(
            name='CtiProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('VIRUSTOTAL', 'VirusTotal'), ('ABUSEIPDB', 'AbuseIPDB'), ('SHODAN', 'Shodan'), ('OTXALIENVAULT', 'OTX AlienVault'), ('MISP', 'MISP')], max_length=30, unique=True)),
                ('api_key', models.CharField(blank=True, default='', max_length=512)),
                ('base_url', models.CharField(blank=True, default='', help_text='Required for self-hosted sources (e.g. MISP).', max_length=255)),
                ('enabled', models.BooleanField(default=True)),
            ],
        ),
        migrations.RunPython(
            code=seed_incident_categories,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            code=seed_default_admin,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            code=load_demo_incidents,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
