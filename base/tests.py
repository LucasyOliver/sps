from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.utils import OperationalError
from django.test import TestCase, override_settings
from django.urls import reverse


class HealthcheckAndWaitForDbTests(TestCase):
    def test_liveness_endpoint_returns_ok_even_without_https_header(self):
        response = self.client.get(reverse('base:healthz'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'check': 'liveness'})

    def test_readiness_endpoint_returns_ready_when_db_available(self):
        response = self.client.get(reverse('base:readyz'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ready', 'database': 'ok'})

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=True)
    def test_proxy_ssl_header_and_healthcheck_redirect_exemption(self):
        health_resp = self.client.get(reverse('base:healthz'))
        self.assertEqual(health_resp.status_code, 200)

        http_resp = self.client.get(reverse('accounts:login'))
        self.assertEqual(http_resp.status_code, 301)

        https_proxied_resp = self.client.get(
            reverse('accounts:login'),
            HTTP_X_FORWARDED_PROTO='https',
        )
        self.assertEqual(https_proxied_resp.status_code, 200)

    def test_wait_for_db_succeeds_immediately_when_db_available(self):
        out = StringIO()
        call_command('wait_for_db', stdout=out)
        self.assertIn('Banco de dados disponivel!', out.getvalue())

    @patch('base.management.commands.wait_for_db.connections')
    def test_wait_for_db_raises_command_error_on_timeout(self, mock_connections):
        mock_connections.__getitem__.return_value.cursor.side_effect = OperationalError(
            'Falha simulada de conexao'
        )
        with self.assertRaises(CommandError):
            call_command('wait_for_db', timeout=1, interval=0.2, stdout=StringIO())
