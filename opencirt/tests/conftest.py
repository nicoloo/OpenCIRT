import os
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crud.settings')


@pytest.fixture
def disable_ssl_redirect(settings):
    # SECURE_SSL_REDIRECT=True (set when DEBUG=False) causes the Django test
    # client (http://testserver) to 301 every request. Apply this fixture
    # explicitly to tests that POST/GET via the test client.
    settings.SECURE_SSL_REDIRECT = False
