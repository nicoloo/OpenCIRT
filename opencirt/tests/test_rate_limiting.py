import pytest
from django.test import TestCase
from django.core.cache import cache
from opencirt.models import User


LOGIN_URL = '/login/'


@pytest.mark.django_db
class TestLoginRateLimit(TestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def tearDown(self):
        cache.clear()

    def _post_login(self, username='baduser', password='badpass', ip='1.2.3.4'):
        return self.client.post(
            LOGIN_URL,
            {'username': username, 'password': password},
            HTTP_X_FORWARDED_FOR=ip,
        )

    def test_ten_failed_attempts_are_allowed(self):
        for _ in range(10):
            response = self._post_login()
            assert response.status_code == 200

    def test_eleventh_attempt_is_blocked(self):
        for _ in range(10):
            self._post_login()
        response = self._post_login()
        assert response.status_code == 429

    def test_different_ips_are_tracked_separately(self):
        for _ in range(10):
            self._post_login(ip='1.2.3.4')
        blocked = self._post_login(ip='1.2.3.4')
        assert blocked.status_code == 429
        allowed = self._post_login(ip='9.9.9.9')
        assert allowed.status_code == 200

    def test_successful_login_not_counted_against_limit(self):
        # 9 failed attempts
        for _ in range(9):
            self._post_login(ip='5.5.5.5')
        # 1 successful login — clears the counter
        self.client.post(
            LOGIN_URL,
            {'username': 'testuser', 'password': 'testpass123'},
            HTTP_X_FORWARDED_FOR='5.5.5.5',
        )
        # Should still be able to attempt (counter was reset)
        response = self._post_login(ip='5.5.5.5')
        assert response.status_code == 200


import json
from unittest.mock import patch
from opencirt.models import Incident, UserRole
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestAiRephraseRateLimit(TestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='analyst', password='pass')
        self.incident = Incident.objects.create(
            name='Test', description='desc', executive_summary='',
            lessons_learned='', technical_details='',
            starting_time=timezone.now(),
            ending_time=timezone.now() + timedelta(hours=1),
            duration=timedelta(hours=1),
            time_to_detect=timedelta(minutes=10),
            time_to_respond=timedelta(minutes=20),
            ai_rephrase_enabled=True,
        )
        UserRole.objects.create(user=self.user, incident=self.incident, role='INCIDENT_LEAD')
        self.client.force_login(self.user)

    def tearDown(self):
        cache.clear()

    def test_twenty_rephrases_allowed(self):
        from opencirt.views import _ai_rephrase_rate_limit_exceeded
        for _ in range(20):
            assert _ai_rephrase_rate_limit_exceeded(self.user.pk) is False

    def test_twenty_first_rephrase_blocked(self):
        from opencirt.views import _ai_rephrase_rate_limit_exceeded
        for _ in range(20):
            _ai_rephrase_rate_limit_exceeded(self.user.pk)
        assert _ai_rephrase_rate_limit_exceeded(self.user.pk) is True
