"""Bounded read-only Reddit probe. Persist counts/field coverage, never credentials/content."""
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener
import boto3
from reddit_access_check import NoRedirect

ROOT = Path(__file__).resolve().parent


def main():
    config = json.loads((ROOT / 'config/reddit-access.json').read_text())
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(), checks=[],
                  authentication_verified=False, historical_completeness_verified=False,
                  commercial_approval_verified=False, collection_enabled=False)
    opener = build_opener(NoRedirect())

    def fetch(request, check):
        report['checks'].append(check)
        try:
            with opener.open(request, timeout=30) as response:
                check['http_status'] = response.status
                check['rate_limits'] = {k: response.headers[k] for k in
                    ('x-ratelimit-remaining', 'x-ratelimit-used', 'x-ratelimit-reset')
                    if response.headers.get(k) is not None}
                raw = response.read(2097153)
            if len(raw) > 2097152:
                raise ValueError('response size limit')
            return json.loads(raw)
        except HTTPError as exc:
            check['http_status'] = exc.code
            exc.close()
            raise

    try:
        secret = json.loads(boto3.client('secretsmanager', region_name=config['region'])
            .get_secret_value(SecretId=config['secret_id'])['SecretString'])
        auth = base64.b64encode((secret[config['client_id_field']].strip() + ':' +
            secret[config['client_secret_field']].strip()).encode()).decode()
        payload = fetch(Request(config['token_endpoint'],
            data=urlencode({'grant_type': 'client_credentials'}).encode(),
            headers={'Authorization': 'Basic ' + auth, 'User-Agent': config['user_agent']}),
            {'kind': 'oauth'})
        token = payload.get('access_token')
        if not isinstance(token, str) or not token:
            raise ValueError('no token')
        report['authentication_verified'] = True

        def get(path, params, check):
            time.sleep(1.1)
            return fetch(Request('https://oauth.reddit.com' + path + '?' + urlencode(params),
                headers={'Authorization': 'Bearer ' + token,
                         'User-Agent': config['user_agent']}), check)

        def summarize(payload, check):
            rows = [c['data'] for c in payload.get('data', {}).get('children', [])
                    if c.get('kind') == 't3']
            check['posts'] = len(rows)
            dates = [r['created_utc'] for r in rows if isinstance(r.get('created_utc'), (int, float))]
            if dates:
                check['oldest_post'] = datetime.fromtimestamp(min(dates), timezone.utc).isoformat()
                check['newest_post'] = datetime.fromtimestamp(max(dates), timezone.utc).isoformat()
            check['field_counts'] = {f: sum(f in r for r in rows) for f in
                ('id', 'title', 'selftext', 'created_utc', 'subreddit', 'score', 'num_comments', 'permalink')}
            check['has_next_page'] = bool(payload.get('data', {}).get('after'))
            return rows

        chosen = None
        for sector, query in [('biotech', 'BeiGene OR biotech'), ('robotics', 'robotics'),
                              ('semiconductors', 'NVIDIA OR semiconductor'),
                              ('energy_storage', 'battery storage')]:
            check = {'kind': 'recent_search', 'sector': sector, 'query': query}
            params = dict(q=query, sort='new', t='all', limit=25, type='link', raw_json=1)
            payload = get('/search', params, check)
            rows = summarize(payload, check)
            if chosen is None:
                chosen = next((r['id'] for r in rows if r.get('num_comments', 0) > 0), None)
            if sector == 'biotech' and payload.get('data', {}).get('after'):
                params['after'] = payload['data']['after']
                next_check = {'kind': 'pagination', 'sector': sector}
                next_rows = summarize(get('/search', params, next_check), next_check)
                next_check['overlap_with_first_page'] = len({r['id'] for r in rows} &
                                                            {r['id'] for r in next_rows})
        check = {'kind': 'all_time_search', 'query': 'biotech'}
        summarize(get('/search', dict(q='biotech', sort='top', t='all', limit=100,
                                      type='link', raw_json=1), check), check)
        if chosen:
            check = {'kind': 'comments'}
            payload = get('/comments/' + chosen, dict(limit=25, depth=3, raw_json=1), check)
            counts = {'comments': 0, 'more_nodes': 0, 'comments_with_body_and_date': 0}

            def walk(listing):
                if not isinstance(listing, dict):
                    return
                for child in listing.get('data', {}).get('children', []):
                    data = child.get('data', {})
                    if child.get('kind') == 't1':
                        counts['comments'] += 1
                        counts['comments_with_body_and_date'] += int('body' in data and 'created_utc' in data)
                        walk(data.get('replies'))
                    elif child.get('kind') == 'more':
                        counts['more_nodes'] += 1
            for listing in payload[1:]:
                walk(listing)
            check.update(counts)
        report['status'] = 'bounded_probe_complete'
    except Exception as exc:
        report['status'] = 'probe_stopped'
        report['error_type'] = type(exc).__name__
    (ROOT / 'reports/reddit-capability-check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'bounded_probe_complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
