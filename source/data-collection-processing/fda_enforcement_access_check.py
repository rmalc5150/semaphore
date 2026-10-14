"""One documented iRES recall lookup; retain only safe structural diagnostics."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener
import boto3
from fda_access import NoRedirect

ROOT = Path(__file__).resolve().parent


def main():
    config = json.loads((ROOT / 'config/fda-enforcement-access.json').read_text())
    report = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'query': 'recalls modified January 2021; maximum one row', 'access_verified': False, 'daily_capture_started': False}
    try:
        secret = json.loads(boto3.client('secretsmanager', region_name=config['region'])
            .get_secret_value(SecretId=config['secret_id'])['SecretString'])
        report['secret_readable'] = True
        user = secret.get(config['user_field']) or secret.get('Authorization-User')
        key = secret.get(config['key_field']) or secret.get('Authorization-Key')
        report['credential_fields_present'] = bool(user and key)
        if not all(isinstance(v, str) and v.strip() for v in (user, key)):
            raise ValueError('missing credentials')
        request = Request(config['probe_endpoint'] + '?' + urlencode({'signature': str(time.time_ns())}),
            data=urlencode({'payload': json.dumps({'displaycolumns': 'productid,recalleventid,recallnum,eventlmd', 'filter': json.dumps([{'eventlmdfrom': '01/01/2021'}, {'eventlmdto': '01/31/2021'}]), 'start': 1, 'rows': 1, 'sort': 'productid', 'sortorder': 'asc'})}).encode(), headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization-User': user.strip(), 'Authorization-Key': key.strip(),
                'User-Agent': 'Optima/1.0 (support@optima-holdings.com)'})
        with build_opener(NoRedirect()).open(request, timeout=40) as response:
            report['http_status'] = response.status
            raw = response.read(2097153)
            report['content_type'] = response.headers.get('Content-Type', '')
        if len(raw) > 2097152:
            raise ValueError('response exceeds limit')
        report['response_bytes'] = len(raw)
        if b'apology' in raw.lower() and b'<html' in raw.lower():
            report['status'] = 'fda_gateway_apology'
        else:
            data = json.loads(raw)
            report['response_type'] = type(data).__name__
            # Structural inspection only; no arbitrary response values saved.
            if isinstance(data, dict):
                report['response_fields'] = sorted(k for k in data if len(k) < 80)
                for k, v in data.items():
                    if k.lower() in ('statuscode', 'resultcount', 'apireturncode') and isinstance(v, (int, float)):
                        report[k.lower()] = v
                    if isinstance(v, list):
                        report.setdefault('list_lengths', {})[k] = len(v)
                result = data.get('RESULT')
                if isinstance(result, dict):
                    report['result_fields'] = sorted(result)
                    report['result_list_lengths'] = {k: len(v) for k, v in result.items() if isinstance(v, list)}
                report['success_message'] = str(data.get('MESSAGE', '')).strip().lower().rstrip('.') in ('success', 'successful')
            elif isinstance(data, list):
                report['records_returned'] = len(data)
            report['status'] = 'response_received_requires_validation'
            count = report.get('resultcount', 0)
            if report.get('success_message') and count > 0:
                report['access_verified'] = True
                report['status'] = 'verified_sample_access'
    except Exception as exc:
        report['status'] = 'failed'
        report['error_type'] = type(exc).__name__
        if isinstance(exc, HTTPError):
            report['http_status'] = exc.code
            exc.close()
    (ROOT / 'reports/fda-enforcement-access-check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
