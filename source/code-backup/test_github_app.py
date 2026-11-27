import base64
import io
import json
import os
import subprocess
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from github_app_auth import GitHubApp, AppError, jwt_token
from github_app_askpass import answer


class AppAuthentication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.pem = cls.key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                        serialization.NoEncryption()).decode()

    def app(self):
        secret = Mock()
        secret.get_secret_value.return_value = {'SecretString': self.pem}
        app = GitHubApp({'repository': 'rmalc5150/semaphore', 'app_id': 5743112,
                         'secret_arn': 'test-secret'}, secrets=secret)
        app.request = Mock(side_effect=[
            {'id': 5743112},
            {'id': 81, 'account': {'login': 'rmalc5150'}, 'permissions': {'contents': 'write'}},
            {'token': 'ephemeral-example-value', 'permissions': {'contents': 'write'},
             'expires_at': datetime.fromtimestamp(time.time() + 3600, timezone.utc).isoformat()},
            {'full_name': 'rmalc5150/semaphore', 'archived': False, 'disabled': False}])
        return app

    def test_jwt_signature_clock_and_issuer(self):
        token = jwt_token(self.pem, 5743112, now=2000000000)
        header, claims, signature = token.split('.')
        decode = lambda s: base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))
        self.assertEqual(json.loads(decode(header))['alg'], 'RS256')
        self.assertEqual(json.loads(decode(claims)), {'iss': '5743112', 'iat': 1999999940, 'exp': 2000000540})
        self.key.public_key().verify(decode(signature), (header + '.' + claims).encode(), padding.PKCS1v15(), hashes.SHA256())

    def test_repository_scope_and_token_reuse_without_global_environment(self):
        app = self.app()
        env = app.environment()
        self.assertEqual(app.token(), env['OPTIMA_GITHUB_INSTALLATION_TOKEN'])
        self.assertEqual(app.request.call_count, 4)
        self.assertEqual(app.request.call_args_list[2].args[2],
                         {'repositories': ['semaphore'], 'permissions': {'contents': 'write'}})
        self.assertNotIn('OPTIMA_GITHUB_INSTALLATION_TOKEN', os.environ)
        self.assertNotIn(env['OPTIMA_GITHUB_INSTALLATION_TOKEN'], app.remote)

    def test_suspended_or_read_only_installation_cannot_mint_token(self):
        for installation in ({'suspended_at': '2026-01-01'},
                             {'account': {'login': 'rmalc5150'}, 'permissions': {'contents': 'read'}}):
            app = self.app()
            app.request.side_effect = [{'id': 5743112}, installation]
            with self.assertRaises(AppError): app.token()
            self.assertEqual(app.request.call_count, 2)

    def test_wrong_app_or_owner_rejected(self):
        app = self.app()
        app.request.side_effect = [{'id': 1}]
        with self.assertRaisesRegex(AppError, 'App ID'): app.token()
        app = self.app()
        app.request.side_effect = [{'id': 5743112}, {'account': {'login': 'other'}, 'permissions': {'contents': 'write'}}]
        with self.assertRaisesRegex(AppError, 'owner mismatch'): app.token()

    def test_archived_repository_rejected(self):
        app = self.app()
        responses = list(app.request.side_effect)
        responses[-1] = {'full_name': 'rmalc5150/semaphore', 'archived': True}
        app.request.side_effect = responses
        with self.assertRaisesRegex(AppError, 'archived'): app.token()

    def test_http_error_never_exposes_response_or_auth(self):
        from urllib.error import HTTPError
        app = self.app()
        app.request = GitHubApp.request.__get__(app)
        app._opener = Mock()
        app._opener.open.side_effect = HTTPError('https://api.github.com/app', 401, 'Unauthorized', {}, io.BytesIO(b'private response'))
        with self.assertRaises(AppError) as error: app.request('/app', 'private-auth-value')
        self.assertNotIn('private', str(error.exception))

    def test_askpass_rejects_other_hosts_and_empty_token(self):
        for prompt in ("Password for 'https://attacker.example': ", "Password for 'http://x-access-token@github.com': "):
            with self.assertRaises(ValueError): answer(prompt, 'ephemeral-example-value')
        with self.assertRaises(ValueError): answer("Username for 'https://github.com': ", '')

    def test_real_git_askpass_works_without_persisting_credentials(self):
        from pathlib import Path
        env = self.app().environment()
        result = subprocess.run(['git', '-c', 'credential.helper=', 'credential', 'fill'],
                                input='protocol=https\nhost=github.com\n\n', env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10,
                                cwd='/tmp')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('username=x-access-token', result.stdout)
        self.assertIn('password=ephemeral-example-value', result.stdout)


if __name__ == '__main__':
    unittest.main()
