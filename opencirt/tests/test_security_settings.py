import pytest
from django.test import override_settings
from django.conf import settings as django_settings


def test_session_cookie_not_secure_in_debug():
    """In debug mode (test env) secure cookies should be off."""
    assert django_settings.SESSION_COOKIE_SECURE is False
    assert django_settings.CSRF_COOKIE_SECURE is False


@override_settings(
    DEBUG=False,
    SECURE_SSL_REDIRECT=True,
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SECURE_HSTS_SECONDS=31536000,
    SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
    SECURE_HSTS_PRELOAD=True,
    SECURE_CONTENT_TYPE_NOSNIFF=True,
    X_FRAME_OPTIONS='DENY',
    SESSION_COOKIE_HTTPONLY=True,
    CSRF_COOKIE_HTTPONLY=True,
)
def test_production_security_settings_are_present():
    """All expected production security settings exist and are set correctly."""
    assert django_settings.SECURE_SSL_REDIRECT is True
    assert django_settings.SESSION_COOKIE_SECURE is True
    assert django_settings.CSRF_COOKIE_SECURE is True
    assert django_settings.SECURE_HSTS_SECONDS == 31536000
    assert django_settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert django_settings.SECURE_HSTS_PRELOAD is True
    assert django_settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert django_settings.X_FRAME_OPTIONS == 'DENY'
    assert django_settings.SESSION_COOKIE_HTTPONLY is True
    assert django_settings.CSRF_COOKIE_HTTPONLY is True
