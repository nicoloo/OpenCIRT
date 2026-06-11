import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0005_incident_tlp'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.CharField(blank=True, default='', max_length=45)),
                ('action', models.CharField(choices=[('CREATE','Create'),('UPDATE','Update'),('DELETE','Delete'),('EXPORT','Export'),('ACCESS','Access')], max_length=10)),
                ('object_type', models.CharField(max_length=50)),
                ('description', models.TextField()),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='opencirt.incident')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-timestamp']},
        ),
    ]
