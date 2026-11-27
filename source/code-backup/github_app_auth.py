"""Repository-scoped GitHub App authentication; private keys stay in memory."""
import base64
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class AppError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def jwt_token(pem, app_id, now=None):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    now = int(time.time() if now is None else now)
    def encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b'=')
    try:
        key = serialization.load_pem_private_key(pem.encode(), password=None)
    except (ValueError, TypeError):
        raise AppError('GitHub App secret is not an unencrypted PEM private key') from None
    if not isinstance(key, rsa.RSAPrivateKey):
        raise AppError('GitHub App requires an RSA private key')
    header = encode(b'{"alg":"RS256","typ":"JWT"}')
    claims = encode(json.dumps({'iat': now - 60, 'exp': now + 540, 'iss': str(app_id)}, separators=(',', ':')).encode())
    message = header + b'.' + claims
    return (message + b'.' + encode(key.sign(message, padding.PKCS1v15(), hashes.SHA256()))).decode()


class GitHubApp:
    def __init__(self, config, secrets=None, opener=None):
        self.config = config
        self.repository = config['repository']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', self.repository):
            raise AppError('Invalid configured GitHub repository')
        self.app_id = int(config['app_id'])
        self.installation_id = None
        self._token = None
        self._expires = 0
        self._secrets = secrets
        self._opener = opener or build_opener(NoRedirect())

    def request(self, path, auth, body=None):
        request = Request('https://api.github.com' + path,
                          data=json.dumps(body).encode() if body is not None else None,
                          headers={'Authorization': 'Bearer ' + auth,
                                   'Accept': 'application/vnd.github+json',
                                   'X-GitHub-Api-Version': '2026-03-10',
                                   'User-Agent': 'Optima-EC2-backup',
                                   'Content-Type': 'application/json'})
        try:
            with self._opener.open(request, timeout=30) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise AppError('GitHub API response exceeds metadata limit')
            return json.loads(raw)
        except HTTPError as error:
            status = error.code
            error.close()
            raise AppError('GitHub API HTTP ' + str(status) + ' at ' + path + '; check app installation, repository selection and permissions') from None
        except URLError:
            raise AppError('Cannot connect to GitHub API at ' + path) from None

    def token(self):
        if self._token and time.time() < self._expires - 300:
            return self._token
        if self._secrets is None:
            import boto3
            self._secrets = boto3.client('secretsmanager', region_name=self.config.get('region', 'us-east-1'))
        secret = self._secrets.get_secret_value(SecretId=self.config['secret_arn'])['SecretString']
        if not secret.lstrip().startswith('-----BEGIN '):
            try:
                fields = json.loads(secret)
                secret = fields.get('private_key') or fields.get('pem')
            except (ValueError, AttributeError):
                raise AppError('GitHub App secret must be PEM text or JSON with private_key/pem') from None
        if not isinstance(secret, str):
            raise AppError('GitHub App private key is missing')
        jwt = jwt_token(secret, self.app_id)
        app = self.request('/app', jwt)
        if app.get('id') != self.app_id:
            raise AppError('GitHub App ID does not match private key')
        installation = self.request('/repos/' + self.repository + '/installation', jwt)
        if installation.get('suspended_at'):
            raise AppError('GitHub App installation is suspended')
        if installation.get('account', {}).get('login', '').lower() != self.repository.split('/')[0].lower():
            raise AppError('GitHub App installation owner mismatch')
        if installation.get('permissions', {}).get('contents') != 'write':
            raise AppError('GitHub App installation needs Contents: read and write')
        if self.config.get('installation_id') and int(self.config['installation_id']) != installation['id']:
            raise AppError('GitHub App installation ID changed; review configuration')
        self.installation_id = installation['id']
        grant = self.request('/app/installations/' + str(self.installation_id) + '/access_tokens', jwt,
                             {'repositories': [self.repository.split('/')[1]], 'permissions': {'contents': 'write'}})
        if not grant.get('token') or grant.get('permissions', {}).get('contents') != 'write':
            raise AppError('GitHub App did not grant a write-capable installation token')
        expires = datetime.fromisoformat(grant['expires_at'].replace('Z', '+00:00')).timestamp()
        if expires <= time.time() + 300:
            raise AppError('GitHub App installation token expires too soon')
        repository = self.request('/repos/' + self.repository, grant['token'])
        if repository.get('full_name', '').lower() != self.repository.lower() or repository.get('archived') or repository.get('disabled'):
            raise AppError('GitHub repository identity mismatch, archived or disabled')
        self._token, self._expires = grant['token'], expires
        return self._token

    def environment(self):
        # Pass the short-lived token only to Git/askpass, never in argv or URLs.
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_TRACE') and k != 'GIT_CURL_VERBOSE'}
        env.update(GIT_ASKPASS=str(Path(__file__).with_name('github_app_askpass.py')),
                   GIT_TERMINAL_PROMPT='0', LC_ALL='C', OPTIMA_GITHUB_INSTALLATION_TOKEN=self.token())
        return env

    @property
    def remote(self):
        return 'https://github.com/' + self.repository + '.git'
