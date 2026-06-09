import django
from django.conf import settings
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crud.settings')
django.setup()
