"""Allowlisted public-source adapters for isolated, date-bounded raw backfills.

These adapters retain current provider responses. They do not assert that today's
versions were publicly available at the historical observation date.
"""
from datetime import date, datetime, timedelta, timezone
import json
import xml.etree.ElementTree as ET

VERSION = 'constellation-raw-v1'
PROVIDERS = {
    'usgs_earthquakes': {'url': 'https://earthquake.usgs.gov/fdsnws/event/1/query',
        'dataset': 'earthquake_events', 'interval_seconds': 2, 'daily_budget': 2000,
        'documentation': 'https://earthquake.usgs.gov/fdsnws/event/1/'},
    'nsf_awards': {'url': 'https://api.nsf.gov/services/v1/awards.json',
        'dataset': 'research_awards', 'interval_seconds': 3, 'daily_budget': 1000,
        'documentation': 'https://resources.research.gov/common/webapi/awardapisearch-v1.htm'},
    'arxiv': {'url': 'https://export.arxiv.org/api/query',
        'dataset': 'preprint_metadata', 'interval_seconds': 4, 'daily_budget': 10000,
        'documentation': 'https://info.arxiv.org/help/api/user-manual.html'}
}


def validate_spec(spec):
    provider = PROVIDERS.get(spec['source_key'])
    if not provider or spec['dataset'] != provider['dataset'] or spec['extractor_version'] != VERSION:
        raise ValueError('Unreviewed source/dataset/extractor; legacy adapters cannot run here')
    if spec['parameters'] != {} or spec['geography'] != 'global' or spec['edition'] != 'current_retrieval':
        raise ValueError('Only the audited global current-retrieval scope is supported')
    start, end = date.fromisoformat(spec['start']), date.fromisoformat(spec['end'])
    if not date(2016, 1, 1) <= start < end <= datetime.now(timezone.utc).date() or (end - start).days > 1:
        raise ValueError('Use a single closed historical UTC day')


def request(spec, cursor):
    validate_spec(spec)
    source = spec['source_key']
    start, end = date.fromisoformat(spec['start']), date.fromisoformat(spec['end'])
    if source == 'usgs_earthquakes':
        # FDSN's endtime is inclusive; preserve our [start,end) contract.
        stop = datetime.combine(end, datetime.min.time()) - timedelta(milliseconds=1)
        params = {'format': 'geojson', 'starttime': start.isoformat(), 'endtime': stop.isoformat(timespec='milliseconds'),
            'limit': 1000, 'offset': int(cursor or 1), 'orderby': 'time-asc', 'nodata': 204}
    elif source == 'nsf_awards':
        params = {'dateStart': start.strftime('%m/%d/%Y'), 'dateEnd': (end - timedelta(days=1)).strftime('%m/%d/%Y'),
            'rpp': 25, 'offset': int(cursor or 1),
            'printFields': 'id,title,abstractText,date,startDate,expDate,awardeeName,awardeeCountryCode,awardeeStateCode,fundsObligatedAmt,agency'}
    else:
        params = {'search_query': 'submittedDate:[' + start.strftime('%Y%m%d') + '0000 TO ' +
            (end - timedelta(days=1)).strftime('%Y%m%d') + '2359]', 'start': int(cursor or 0),
            'max_results': 100, 'sortBy': 'submittedDate', 'sortOrder': 'ascending'}
    return PROVIDERS[source]['url'], params


def parse(spec, body, cursor, http_status=200):
    source = spec['source_key']
    if http_status == 204:
        if source == 'usgs_earthquakes' and not body:
            return [], None
        raise ValueError('Unexpected no-content response')
    if source == 'usgs_earthquakes':
        data = json.loads(body)
        if data.get('type') != 'FeatureCollection' or not isinstance(data.get('features'), list):
            raise ValueError('USGS response shape')
        rows = data['features']
        for row in rows:
            when = datetime.fromtimestamp(row['properties']['time'] / 1000, timezone.utc).date()
            if not date.fromisoformat(spec['start']) <= when < date.fromisoformat(spec['end']):
                raise ValueError('USGS event outside requested partition')
        return rows, (int(cursor or 1) + len(rows)) if len(rows) == 1000 else None
    if source == 'nsf_awards':
        data = json.loads(body)
        response = data.get('response', {})
        rows = response.get('award')
        if not isinstance(rows, list):
            raise ValueError('NSF response shape; provider error is not an empty partition')
        for row in rows:
            when = datetime.strptime(row['date'], '%m/%d/%Y').date()
            if not date.fromisoformat(spec['start']) <= when < date.fromisoformat(spec['end']):
                raise ValueError('NSF award outside requested partition')
        return rows, (int(cursor or 1) + len(rows)) if len(rows) == 25 else None
    root = ET.fromstring(body)
    ns = {'atom': 'http://www.w3.org/2005/Atom', 'os': 'http://a9.com/-/spec/opensearch/1.1/'}
    total = int(root.findtext('os:totalResults', namespaces=ns))
    rows = []
    for node in root.findall('atom:entry', ns):
        row = {field: node.findtext('atom:' + field, namespaces=ns) for field in ('id', 'title', 'summary', 'published', 'updated')}
        row['authors'] = [author.findtext('atom:name', namespaces=ns) for author in node.findall('atom:author', ns)]
        row['categories'] = [category.get('term') for category in node.findall('atom:category', ns)]
        if not row['id'] or '/abs/' not in row['id']:
            raise ValueError('arXiv error or invalid entry')
        if not spec['start'] <= row['published'][:10] < spec['end']:
            raise ValueError('arXiv submission outside requested partition')
        rows.append(row)
    next_offset = int(cursor or 0) + len(rows)
    if next_offset < total and not rows:
        raise ValueError('arXiv pagination truncated')
    return rows, next_offset if next_offset < total else None


def identity(spec, row):
    return str(row['id'])


def observation(spec, row, raw_uri, retrieved_at):
    source = spec['source_key']
    if source == 'usgs_earthquakes':
        properties = row['properties']
        observed = datetime.fromtimestamp(properties['time'] / 1000, timezone.utc).isoformat()
        published = None
        url = properties.get('url')
    elif source == 'nsf_awards':
        observed = datetime.strptime(row['date'], '%m/%d/%Y').date().isoformat()
        published = None
        url = 'https://www.nsf.gov/awardsearch/showAward?AWD_ID=' + row['id']
    else:
        observed, published, url = row['published'], row['published'], row['id']
    return {'source_key': source, 'source_record_id': identity(spec, row), 'record_kind': spec['dataset'],
        'original_url': url, 'raw_s3_uri': raw_uri, 'observation_start_at': observed,
        'first_published_at': published, 'available_to_market_at': None,
        'availability_basis': 'not_verified_for_retrieved_version', 'edition_id': 'current_retrieval',
        'retrieved_at': retrieved_at, 'parser_version': VERSION,
        'quality_flags': ['historical_vintage_not_verified', 'entity_resolution_pending', 'commercial_ml_rights_not_audited'],
        'payload': row}
