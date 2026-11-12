"""Resolve openFDA credentials without putting secrets in diagnostics."""
import json
import os
from functools import lru_cache
from pathlib import Path
from urllib.request import HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@lru_cache(maxsize=1)
def api_key():
    from regulatory_collection import SourceIssue
    try:
        value = os.environ.get('OPENFDA_API_KEY')
        if not value:
            import boto3
            config = json.loads((Path(__file__).parent / 'config/fda-access.json').read_text())
            secret = boto3.client('secretsmanager', region_name=config['region']).get_secret_value(
                SecretId=config['secret_id'])
            value = json.loads(secret['SecretString'])[config['secret_field']]
        if not isinstance(value, str) or not value.strip():
            raise ValueError('missing key')
        return value.strip()
    except Exception:
        raise SourceIssue('openfda_credential_unavailable', True) from None
