"""Bounded official authenticated sources; current retrieval is not a past vintage."""
from datetime import date, timedelta
from functools import lru_cache
import json
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from research_contract import ROOT, canonical_json, digest, load_json
from regulatory_collection import SourceIssue, require
from fda_access import NoRedirect

KINDS = {'fda_dashboard', 'fda_enforcement', 'fda_productcodes', 'edinet', 'eia_api', 'sam_gov'}


@lru_cache(maxsize=8)
def credentials(name):
    try:
        import boto3
        config = load_json(ROOT / ('config/' + name + '-access.json'))
        raw = boto3.client('secretsmanager', region_name=config['region']).get_secret_value(SecretId=config['secret_id'])
        data = json.loads(raw['SecretString'])
        if 'user_field' in config:
            values = (data.get(config['user_field']) or data.get('Authorization-User'),
                      data.get(config['key_field']) or data.get('Authorization-Key'))
        else:
            values = (data[config['secret_field']],)
        require(all(isinstance(v, str) and v.strip() for v in values), 'credential_fields_missing')
        return tuple(v.strip() for v in values)
    except Exception:
        raise SourceIssue('credential_unavailable', True) from None


def request(client, name, url, params=None, body=None, form=False):
    """No credential-bearing URLs/errors or response echoes enter saved evidence."""
    values = credentials(name)
    public = url + ('?' + urlencode(params) if params else '')
    query = dict(params or {})
    headers = {'User-Agent': 'Optima/1.0 (support@optima-holdings.com)'}
    if len(values) == 2:
        headers.update({'Authorization-User': values[0], 'Authorization-Key': values[1]})
    else:
        query['Subscription-Key' if name == 'edinet' else 'api_key'] = values[0]
    data = None
    if body is not None:
        headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
        data = urlencode({'payload': json.dumps(body) if isinstance(body, dict) else body}).encode() if form else canonical_json(body)
    try:
        with build_opener(NoRedirect()).open(Request(url + ('?' + urlencode(query) if query else ''),
                data=data, headers=headers), timeout=40) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
        require(len(raw) <= 16 * 1024 * 1024, 'authenticated_response_too_large')
        payload = json.loads(raw)
        # EIA echoes API keys. Redact auth values throughout the JSON before evidence persistence.
        safe = json.dumps(payload)
        for value in values:
            safe = safe.replace(json.dumps(value)[1:-1], '[REDACTED]')
        client.save(safe.encode(), public)
        return json.loads(safe) if name == 'sam-gov' else payload
    except SourceIssue:
        raise
    except HTTPError as exc:
        status = exc.code; exc.close()
        raise SourceIssue('source_http_' + str(status), status in (429, 500, 502, 503, 504)) from None
    except Exception:
        raise SourceIssue('authenticated_source_request_failed', True) from None


def sam_request_budget():
    """Shared daily/hourly admission budget for daily and backfill requests."""
    import fcntl
    from datetime import datetime, timezone
    from research_contract import ROOT
    config = load_json(ROOT / 'config/sam-gov-access.json')
    with (ROOT / '.sam-gov-quota.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = ROOT / 'reports/sam-gov-quota.json'
        current = time.time()
        today = datetime.now(timezone.utc).date().isoformat()
        state = json.loads(path.read_text()) if path.exists() else {}
        calls = state.get('calls', []) if state.get('date') == today else []
        require(len(calls) < config.get('daily_request_budget', 40), 'sam_daily_request_budget')
        require(sum(t > current - 3600 for t in calls) < config.get('hourly_request_budget', 10), 'sam_hourly_request_budget')
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'date': today, 'calls': calls + [current]}))
        temporary.replace(path)


def scopes(source, start, end, mode):
    kind = source['adapter']
    if kind == 'fda_productcodes':
        if mode == 'historical':
            return
        yield start, end, {'url': source['api']}, 'Current FDA industry code reference only; no historical code vintages'
        return
    if kind == 'edinet':
        cursor = start
        while cursor < end:
            stop = cursor + timedelta(days=1)
            yield cursor, stop, {'url': source['api'], 'date': str(cursor)}, 'EDINET daily filing metadata inventory; all issuers, unresolved company links; original filings require separate document download'
            cursor = stop
        return
    from specialist_plan import months
    for begin, stop in months(start, end):
        begin = max(begin, start)
        yield begin, stop, {'url': source['api'], 'start': str(begin), 'end': str(stop),
            **{k: source[k] for k in ('date_field', 'id_fields') if k in source}}, source['coverage_note']


def fetch(client, job, cursor, item):
    p = job['parameters']; kind = job['adapter']; url = p['url']
    if kind == 'sam_gov':
        page = int(cursor or 0)
        require(page >= 0, 'sam_invalid_page')
        size = 1000
        last = date.fromisoformat(p['end']) - timedelta(days=1)
        sam_request_budget()
        data = request(client, 'sam-gov', url, {
            'postedFrom': date.fromisoformat(p['start']).strftime('%m/%d/%Y'),
            'postedTo': last.strftime('%m/%d/%Y'), 'limit': size, 'offset': page})
        rows, total = data.get('opportunitiesData'), data.get('totalRecords')
        require(isinstance(rows, list) and type(total) is int and total >= 0, 'sam_response_shape')
        require(data.get('offset') == page and data.get('limit') == size, 'sam_pagination_mismatch')
        require(len(rows) <= size and page * size + len(rows) <= total, 'sam_count_mismatch')
        require(bool(rows) or total == page == 0, 'sam_missing_page')
        require(all(isinstance(r, dict) and r.get('noticeId') and
                    p['start'] <= str(r.get('postedDate', ''))[:10] < p['end'] for r in rows), 'sam_record_scope')
        require(len({r['noticeId'] for r in rows}) == len(rows), 'sam_duplicate_notice')
        more = (page + 1) * size < total
        require(not more or len(rows) == size, 'sam_short_nonterminal_page')
        return [item(r['noticeId'], r, r.get('uiLink') or url, str(r['postedDate'])[:10]) for r in rows], str(page + 1) if more else None
    offset = int(cursor or 0); size = p.get('page_size', 100)
    require(isinstance(size, int) and 1 <= size <= 100, 'authenticated_page_size')
    if kind == 'edinet':
        data = request(client, 'edinet', url, {'date': p['date'], 'type': 2})
        require(str(data.get('metadata', {}).get('status')) == '200', 'edinet_api_status')
        rows = data.get('results')
        count = data.get('metadata', {}).get('resultset', {}).get('count')
        require(isinstance(rows, list) and count is not None and int(count) == len(rows), 'edinet_inventory_count')
        require(all(r.get('docID') for r in rows), 'edinet_missing_id')
        return [item(r['docID'], r, url, p['date']) for r in rows], None
    if kind == 'fda_productcodes':
        data = request(client, 'fda-productcodes', url, {'signature': str(time.time_ns())})
        rows = table_rows(data)
        require(len(rows) == int(data.get('RESULTCOUNT', -1)), 'pcb_incomplete_reference')
        return [item(digest(r), r, url, basis='derived') for r in rows], None
    last = date.fromisoformat(p['end']) - timedelta(days=1)
    if kind == 'eia_api':
        params = {'frequency': 'monthly', 'data[0]': 'price', 'facets[stateid][]': 'US',
                  'facets[sectorid][]': 'ALL', 'start': p['start'][:7], 'end': str(last)[:7],
                  'sort[0][column]': 'period', 'sort[0][direction]': 'asc', 'offset': offset, 'length': size}
        data = request(client, 'eia', url, params)
        require(not data.get('error'), 'eia_api_error')
        result = data.get('response', {}); rows = result.get('data'); total = int(result.get('total', -1))
        require(isinstance(rows, list), 'eia_rows')
        require(all(r.get('stateid') == 'US' and r.get('sectorid') == 'ALL'
                    and p['start'][:7] <= r.get('period', '') <= str(last)[:7] for r in rows), 'eia_scope_mismatch')
        output = [item('US:ALL:' + r['period'], r, url) for r in rows]
    elif kind == 'fda_dashboard':
        field = p['date_field']
        data = request(client, 'fda-dashboard', url, body={'start': offset + 1, 'rows': size,
            'sort': '', 'sortorder': 'ASC', 'returntotalcount': True, 'columns': [],
            'filters': {field + 'From': [p['start']], field + 'To': [str(last)]}})
        require(data.get('statuscode') in (400, 412), 'ddapi_status')
        rows = data.get('result'); total = int(data.get('totalrecordcount', 0 if data.get('statuscode') == 412 else -1))
        require(isinstance(rows, list) and data.get('resultcount') == len(rows), 'ddapi_rows')
        require(all(p['start'] <= str(r.get(field, ''))[:10] < p['end'] for r in rows), 'ddapi_date_outside_window')
        # Citations/classifications may share inspection IDs; full row identity preserves distinct source observations.
        output = [item(digest(r), r, url, str(r[field])[:10], 'derived') for r in rows]
    else:
        data = request(client, 'fda-enforcement', url, {'signature': str(time.time_ns())}, body={
            'displaycolumns': 'productid,recalleventid,recallnum,eventlmd,recallinitiationdt,productdescriptiontxt,productshortreasontxt,firmlegalnam,firmfeinum,centerclassificationtypetxt,enforcementreportdt',
            'filter': json.dumps([{'eventlmdfrom': date.fromisoformat(p['start']).strftime('%m/%d/%Y')},
                                  {'eventlmdto': last.strftime('%m/%d/%Y')}]),
            'start': offset + 1, 'rows': size, 'sort': 'productid', 'sortorder': 'asc'}, form=True)
        rows = table_rows(data); total = int(data.get('RESULTCOUNT', -1))
        lowered = [{k.lower(): v for k, v in r.items()} for r in rows]
        require(all(r.get('productid') is not None for r in lowered), 'ires_missing_id')
        output = [item(r['productid'], r, url) for r in lowered]
    require(total >= 0 and offset + len(rows) <= total, 'authenticated_count_mismatch')
    require(bool(rows) or offset == total, 'authenticated_missing_page')
    return output, str(offset + len(rows)) if offset + len(rows) < total else None


def table_rows(data):
    require(data.get('STATUSCODE', data.get('APIRETURNCODE')) in (400, 412), 'fda_api_status')
    rows = data.get('RESULT')
    if isinstance(rows, dict):
        columns, values = rows.get('COLUMNS'), rows.get('DATA')
        require(isinstance(columns, list) and isinstance(values, list), 'fda_table_shape')
        require(all(isinstance(v, list) and len(v) == len(columns) for v in values), 'fda_table_width')
        rows = [dict(zip(columns, v)) for v in values]
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows), 'fda_result_shape')
    return rows
