"""Bounded manual API probes; no scheduler activation or coverage-complete claim."""
from datetime import datetime, timezone
import json
from pathlib import Path
import threading

import requests

from constellation.control import Control, canonical
from constellation.sources import PROVIDERS, VERSION, request, parse
from constellation.worker import put_verified, MAX_BODY


def main():
    control = Control()
    if control.allowed():
        raise RuntimeError('Probe expects the backfill scheduler to be paused')
    results = []
    for source in PROVIDERS:
        spec = {'source_key': source, 'dataset': PROVIDERS[source]['dataset'],
            'geography': 'global', 'start': '2016-01-04', 'end': '2016-01-05',
            'edition': 'current_retrieval', 'extractor_version': VERSION, 'parameters': {}}
        url, params = request(spec, None)
        try:
            with requests.get(url, params=params, stream=True, timeout=(10, 30), allow_redirects=False,
                    headers={'User-Agent': 'ConstellationResearch/1.0 (support@optima-holdings.com)'}) as response:
                chunks = []
                size = 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > MAX_BODY:
                        raise ValueError('Response exceeds bounded probe budget')
                    chunks.append(chunk)
                body = b''.join(chunks)
                when = datetime.now(timezone.utc).isoformat()
                prefix = control.config['prefix'] + '/probes/' + source + '/' + when.replace(':', '-')
                raw = put_verified(control, prefix + '/raw', body, response.headers.get('Content-Type', 'application/octet-stream'))
                result = {'source_key': source, 'spec': spec, 'http_status': response.status_code,
                    'request_url': response.url, 'retrieved_at': when, 'raw': raw,
                    'historical_complete': False, 'documentation': PROVIDERS[source]['documentation']}
                if response.status_code >= 400:
                    result.update(status='probe_failed', reason='provider_http_' + str(response.status_code))
                    saved = put_verified(control, prefix + '/receipt.json', canonical(result), 'application/json')
                    result['receipt_uri'] = saved['uri']
                    results.append(result)
                    continue
                rows, cursor = parse(spec, body, None, http_status=response.status_code)
                result.update(status='validated_sample', records=len(rows), more_pages=cursor is not None)
                saved = put_verified(control, prefix + '/receipt.json', canonical(result), 'application/json')
                result['receipt_uri'] = saved['uri']
                results.append(result)
        except Exception as exc:
            results.append({'source_key': source, 'status': 'probe_failed', 'error': type(exc).__name__,
                'reason': str(exc)[:250], 'historical_complete': False})
    path = Path(__file__).resolve().parent / 'source-probes.json'
    path.write_text(json.dumps({'checked_at': datetime.now(timezone.utc).isoformat(), 'results': results}, indent=2) + '\n')
    print(json.dumps(results))


if __name__ == '__main__':
    main()
