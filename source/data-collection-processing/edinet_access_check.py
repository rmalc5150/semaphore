"""Bounded EDINET credential/access check; never log keys or request URLs."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request

import boto3

ROOT = Path(__file__).resolve().parent


def main():
    config = json.loads((ROOT / 'config/edinet-access.json').read_text())
    report = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'secret_id': config['secret_id'], 'checks': [],
              'daily_capture_started': False, 'historical_collection_complete': False}
    try:
        secret = boto3.client('secretsmanager', region_name=config['region']).get_secret_value(
            SecretId=config['secret_id'])
        key = json.loads(secret['SecretString'])[config['secret_field']]
        if not isinstance(key, str) or not key.strip():
            raise ValueError('invalid key format')
        report['secret_readable'] = True

        def fetch(path, params, limit):
            url = config['api_base'] + path + '?' + urlencode({**params, 'Subscription-Key': key.strip()})
            request = Request(url, headers={'User-Agent': 'Optima-EDINET-access-check/1.0'})
            # Do not follow redirects carrying a key to another endpoint.
            from urllib.request import build_opener, HTTPRedirectHandler
            class NoRedirect(HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None
            with build_opener(NoRedirect()).open(request, timeout=45) as response:
                body = response.read(limit + 1)
                if len(body) > limit:
                    raise ValueError('response exceeds probe limit')
                return response.status, body

        for day in ('2026-10-09', '2021-01-04'):
            status, body = fetch('/documents.json', {'date': day, 'type': 2}, 8 * 1024 * 1024)
            data = json.loads(body)
            metadata = data.get('metadata', {})
            records = data.get('results', [])
            valid = str(metadata.get('status')) == '200' and isinstance(records, list)
            report['checks'].append({'date': day, 'http_status': status,
                'api_status': metadata.get('status'), 'records': len(records),
                'sha256': hashlib.sha256(body).hexdigest(), 'valid': valid})
            if not valid:
                break
            document = next((r for r in records if r.get('pdfFlag') == '1'
                            and r.get('withdrawalStatus') == '0' and r.get('disclosureStatus') == '0'), None)
            if document:
                import re
                doc_id = document['docID']
                if not re.fullmatch(r'[A-Za-z0-9]+', doc_id):
                    raise ValueError('invalid document identifier')
                time.sleep(3)
                status, pdf = fetch('/documents/' + doc_id, {'type': 2}, 16 * 1024 * 1024)
                report['checks'].append({'date': day, 'document_id': doc_id,
                    'http_status': status, 'bytes': len(pdf),
                    'sha256': hashlib.sha256(pdf).hexdigest(), 'valid_pdf': pdf.startswith(b'%PDF-')})
            time.sleep(3)
        report['status'] = 'verified_sample_access' if len(report['checks']) == 4 and all(
            item.get('valid', item.get('valid_pdf', False)) for item in report['checks']) else 'incomplete'
    except Exception as exc:
        # Exception strings can contain the credential-bearing request URL.
        report['status'] = 'failed'
        report['error_type'] = type(exc).__name__
        if isinstance(exc, HTTPError):
            report['http_status'] = exc.code
        if hasattr(exc, 'response') and isinstance(exc.response, dict):
            report['aws_error_code'] = exc.response.get('Error', {}).get('Code')
    path = ROOT / 'reports/edinet-access-check.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return 0 if report['status'] == 'verified_sample_access' else 1


if __name__ == '__main__':
    raise SystemExit(main())
