"""Three bounded authenticated openFDA checks; save whitelisted metadata only."""
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import Request, build_opener
from urllib.parse import urlencode
from urllib.error import HTTPError
from reddit_access_check import NoRedirect
from fda_access import api_key


def main():
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'checks': [],
              'historical_collection_complete': False}
    try:
        auth = base64.b64encode((api_key() + ':').encode()).decode()
        for label, path, query in [
            ('applications', 'drug/drugsfda', {}),
            ('january_2021', 'drug/drugsfda', {'search': 'submissions.submission_status_date:[20210101 TO 20210131]'}),
            ('public_crls', 'transparency/crl', {})]:
            check = {'query': label}
            report['checks'].append(check)
            request = Request('https://api.fda.gov/' + path + '.json?' + urlencode({'limit': 1, **query}),
                headers={'Authorization': 'Basic ' + auth, 'User-Agent': 'Optima support@optima-holdings.com'})
            with build_opener(NoRedirect()).open(request, timeout=30) as response:
                check['http_status'] = response.status
                raw = response.read(2097153)
            if len(raw) > 2097152:
                raise ValueError('oversize response')
            data = json.loads(raw)
            check['records_returned'] = len(data.get('results', []))
            check['total_matches'] = data.get('meta', {}).get('results', {}).get('total')
            check['valid'] = check['records_returned'] == 1 and not data.get('error')
        report['status'] = 'verified_sample_access' if all(c['valid'] for c in report['checks']) else 'incomplete'
    except Exception as exc:
        report['status'] = 'failed'
        report['error_type'] = type(exc).__name__
        if isinstance(exc, HTTPError):
            report['http_status'] = exc.code
            exc.close()
    (Path(__file__).parent / 'reports/fda-access-check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return int(report['status'] != 'verified_sample_access')


if __name__ == '__main__':
    raise SystemExit(main())
