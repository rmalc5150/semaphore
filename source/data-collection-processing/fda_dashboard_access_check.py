"""Bounded DDAPI samples; never save credentials or raw error responses."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener
import boto3
from fda_access import NoRedirect

ROOT = Path(__file__).resolve().parent


def main():
    config = json.loads((ROOT / 'config/fda-dashboard-access.json').read_text())
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'checks': [],
              'secret_readable': False, 'historical_collection_complete': False,
              'daily_capture_started': False}
    try:
        secret = json.loads(boto3.client('secretsmanager', region_name=config['region'])
            .get_secret_value(SecretId=config['secret_id'])['SecretString'])
        report['secret_readable'] = True
        # Accept both the suggested JSON names and FDA's literal header names.
        user = secret.get(config['user_field']) or secret.get('Authorization-User')
        key = secret.get(config['key_field']) or secret.get('Authorization-Key')
        report['credential_fields_present'] = bool(user and key)
        if not all(isinstance(v, str) and v.strip() for v in (user, key)):
            raise ValueError('required fields absent')
        checks = [(e, d, {}) for e, d in [
            ('inspections_classifications', 'InspectionEndDate'),
            ('inspections_citations', 'InspectionEndDate'),
            ('compliance_actions', 'ActionTakenDate'),
            ('import_refusals', 'RefusalDate')]]
        checks.append(('inspections_classifications', 'InspectionEndDate',
                       {'InspectionEndDateFrom': ['2021-01-01'], 'InspectionEndDateTo': ['2021-01-31']}))
        for endpoint, date_field, filters in checks:
            check = {'endpoint': endpoint, 'scope': 'january_2021' if filters else 'latest'}
            report['checks'].append(check)
            body = {'start': 1, 'rows': 1, 'sort': date_field, 'sortorder': 'DESC',
                    'filters': filters, 'columns': []}
            request = Request(config['base_url'] + '/' + endpoint, data=json.dumps(body).encode(),
                headers={'Content-Type': 'application/json', 'Authorization-User': user.strip(),
                         'Authorization-Key': key.strip(), 'User-Agent': 'Optima support@optima-holdings.com'})
            try:
                with build_opener(NoRedirect()).open(request, timeout=40) as response:
                    check['http_status'] = response.status
                    raw = response.read(2097153)
                if len(raw) > 2097152:
                    raise ValueError('response exceeds limit')
                data = json.loads(raw)
                check['api_statuscode'] = data.get('statuscode')
                rows = data.get('result')
                check['records_returned'] = len(rows) if isinstance(rows, list) else 0
                check['valid'] = (data.get('statuscode') == 400 and isinstance(rows, list)
                                  and len(rows) == 1 and data.get('resultcount') == 1)
                if check['valid']:
                    check['sample_date'] = rows[0].get(date_field)
                    check['future_dated_sample'] = (str(check['sample_date'])[:10] > report['checked_at'][:10]
                                                   if check['sample_date'] else False)
                    check['field_names'] = sorted(rows[0])
                    if filters:
                        check['valid'] = str(check['sample_date']).startswith('2021-01-')
            except HTTPError as exc:
                check['http_status'] = exc.code
                check['valid'] = False
                exc.close()
                if exc.code in (401, 403, 429):
                    break
        report['status'] = ('verified_sample_access' if len(report['checks']) == 5
            and all(c.get('valid') for c in report['checks']) else 'incomplete')
    except Exception as exc:
        report['status'] = 'failed'
        report['error_type'] = type(exc).__name__
    (ROOT / 'reports/fda-dashboard-access-check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return int(report['status'] != 'verified_sample_access')


if __name__ == '__main__':
    raise SystemExit(main())
