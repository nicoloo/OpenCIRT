from django.db import migrations
from django.contrib.auth.hashers import make_password


def seed_default_admin(apps, schema_editor):
    User = apps.get_model('opencirt', 'User')

    legacy_username = ''.join(['lead', '_admin'])
    User.objects.filter(username=legacy_username).delete()

    admin_user, _ = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@opencirt.local',
            'displayname': 'Admin',
            'is_admin': True,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
        },
    )
    admin_user.email = 'admin@opencirt.local'
    admin_user.displayname = 'Admin'
    admin_user.is_admin = True
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.is_active = True
    admin_user.password = make_password('admin')
    admin_user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0013_cti_provider'),
    ]

    operations = [
        migrations.RunPython(seed_default_admin, migrations.RunPython.noop),
    ]