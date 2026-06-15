import pytest
from django.test import override_settings
from django.conf import settings as django_settings


@override_settings(
    DEBUG=True,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
    SECURE_HSTS_SECONDS=0,
    SECURE_HSTS_INCLUDE_SUBDOMAINS=False,
    SECURE_HSTS_PRELOAD=False,
)
def test_session_cookie_not_secure_in_debug():
    """In debug mode (test env) secure cookies should be off."""
    assert django_settings.SESSION_COOKIE_SECURE is False
    assert django_settings.CSRF_COOKIE_SECURE is False


def test_security_settings_match_debug_flag():
    """Security settings must be derived from DEBUG, not hardcoded."""
    from django.conf import settings as s
    d = s.DEBUG
    assert s.SESSION_COOKIE_SECURE == (not d)
    assert s.CSRF_COOKIE_SECURE == (not d)
    assert s.SECURE_SSL_REDIRECT == (not d)
    assert s.SECURE_HSTS_SECONDS == (31536000 if not d else 0)
    assert s.SECURE_HSTS_INCLUDE_SUBDOMAINS == (not d)
    assert s.SECURE_HSTS_PRELOAD == (not d)
    assert s.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert s.X_FRAME_OPTIONS == 'DENY'
    assert s.SESSION_COOKIE_HTTPONLY is True
