"""Weekly capture of the accepted fixed-query DataForSEO sample scope."""
import base64
import json
from datetime import datetime, timezone, timedelta

import weekly_readiness as capture
import readiness_publication as publication


def main():
    date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    scope = json.loads((capture.ROOT / 'config/readiness-search-scope.json').read_text())
    capture.OUT = capture.ROOT / 'reports' / ('search-capture-' + date)
    capture.PREFIX = 'research-data/search-capture/' + date
    publication.OUT, publication.PREFIX = capture.OUT, capture.PREFIX
    capture.save('scope.json', scope)
    secret = json.loads(capture.client('secretsmanager').get_secret_value(SecretId=capture.SECRET)['SecretString'])
    token = secret['base64'].strip()
    if token.lower().startswith('basic '):
        token = token[6:]
    assert ':' in base64.b64decode(token).decode(), 'Invalid credential format'
    auth = 'Basic ' + token
    keywords = [p['query'] for p in scope['pilot']]
    plans = []
    # Keyword metrics update at provider cadence; capture once per calendar
    # month. Scope-version changes deliberately require a fresh acceptance.
    month = date[:7]
    marker = capture.ROOT / 'reports' / ('search-keyword-month-' + month + '.json')
    if not marker.exists():
        plans.append(('dataforseo-keyword-history', 'dataforseo_labs/google/historical_keyword_data/live',
            {'keywords': keywords, 'location_code': 2840, 'language_code': 'en'}))
    plans.append(('dataforseo-trends', 'keywords_data/dataforseo_trends/explore/live',
        {'keywords': keywords[:3], 'location_code': 2840, 'type': 'web', 'date_from': scope['historical_start'],
         'date_to': (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()}))
    plans += [('dataforseo-serp-' + str(i), 'serp/google/organic/live/advanced',
        {'keyword': p['query'], 'location_code': 2840, 'language_code': 'en', 'device': 'desktop', 'depth': 10})
        for i, p in enumerate(scope['pilot'])]
    cost = 0.0
    for name, endpoint, payload in plans:
        # Conservative per-request reservation; never issue an additional
        # paid call once the remaining USD 1 run budget is too small.
        reservation = 0.10 if 'keyword-history' in name else 0.02
        if cost + reservation > 1:
            raise RuntimeError('Run budget exhausted')
        receipt = capture.capture(name, 'S65', 'https://api.dataforseo.com/v3/' + endpoint, [payload], auth)
        data = receipt['data'] or {}
        cost += float(data.get('cost', 0))
        capture.save('dataforseo-cost.json', {'actual_cost_usd': cost, 'budget_usd': 1, 'observed_at': capture.now()})
        if receipt['http_status'] != 200 or data.get('status_code') != 20000 or any(t.get('status_code') != 20000 for t in data.get('tasks', [])):
            raise RuntimeError('Provider task failed; inspect saved receipt; no automatic paid retry')
    publication.publish()
    if any(p[0] == 'dataforseo-keyword-history' for p in plans):
        marker.write_text(json.dumps({'month': month, 'scope_version': scope['version'], 'receipt': str(capture.OUT / 'publication.json')}))


if __name__ == '__main__':
    main()
