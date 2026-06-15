from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


_KNOWN_INSECURE_KEYS = {
    'change-me-in-production',
    'django-insecure-nsc+0)*z!9m50@3*lp&1(sq6&%9zk(9r*=q=$j=g*9*-_7h3jn',
}
_MIN_SECRET_KEY_LENGTH = 50


def _validate_production_config():
    from django.conf import settings
    if settings.DEBUG:
        return
    key = settings.SECRET_KEY
    if not key or key in _KNOWN_INSECURE_KEYS or len(key) < _MIN_SECRET_KEY_LENGTH:
        raise ImproperlyConfigured(
            "SECRET_KEY is insecure or too short. "
            "Generate a strong key (50+ random characters) before deploying. "
            "Use: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
        )


class OpencirtConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opencirt'

    def ready(self):
        _validate_production_config()
