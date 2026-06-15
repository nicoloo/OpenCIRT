import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings


INSECURE_KEY = 'django-insecure-nsc+0)*z!9m50@3*lp&1(sq6&%9zk(9r*=q=$j=g*9*-_7h3jn'
PLACEHOLDER_KEY = 'change-me-in-production'

from opencirt.apps import _validate_production_config


def test_guard_passes_in_debug_mode_with_bad_key():
    with override_settings(DEBUG=True, SECRET_KEY=INSECURE_KEY):
        _validate_production_config()  # should not raise


def test_guard_passes_in_production_with_strong_key():
    with override_settings(DEBUG=False, SECRET_KEY='a' * 50):
        _validate_production_config()  # should not raise


def test_guard_raises_with_insecure_default_key():
    with override_settings(DEBUG=False, SECRET_KEY=INSECURE_KEY):
        with pytest.raises(ImproperlyConfigured, match='SECRET_KEY'):
            _validate_production_config()


def test_guard_raises_with_placeholder_key():
    with override_settings(DEBUG=False, SECRET_KEY=PLACEHOLDER_KEY):
        with pytest.raises(ImproperlyConfigured, match='SECRET_KEY'):
            _validate_production_config()


def test_guard_raises_with_short_key():
    with override_settings(DEBUG=False, SECRET_KEY='tooshort'):
        with pytest.raises(ImproperlyConfigured, match='SECRET_KEY'):
            _validate_production_config()
