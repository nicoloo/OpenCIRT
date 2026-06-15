import os
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crud.settings')


@pytest.fixture(autouse=True)
def disable_ssl_redirect(settings):
    # SECURE_SSL_REDIRECT=True (set when DEBUG=False) causes the test client,
    # which uses http://testserver, to get a 301 on every request.
    settings.SECURE_SSL_REDIRECT = False
