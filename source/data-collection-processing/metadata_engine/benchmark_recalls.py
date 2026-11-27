"""Match MLPerf records and CPSC recalls to their immutable original bytes."""
import csv
import hashlib
import io
import json
import re
from datetime import date, timedelta
from functools import lru_cache
from urllib.parse import parse_qs, unquote, urlsplit

from research_contract import digest
IDENTITY_FIELDS = ('ID','PrivateID','Location','Model','MlperfModel','UsedModel','Scenario','Category','Division','Suite','System','SystemName','Units')
LEGACY_IDENTITY_FIELDS = ('ID','PrivateID','Location','Model','Scenario','Category','Division','Suite','System','SystemName')


class ProviderError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise ProviderError(reason)


@lru_cache(maxsize=1)
def json_body(body):
    try:
        return json.loads(body)
    except (ValueError, UnicodeError):
        raise ProviderError('invalid_original_json') from None


def cpsc(body, record, url):
    u = urlsplit(url)
    require(u.scheme == 'https' and u.netloc == 'www.saferproducts.gov'
            and u.path.rstrip('/') == '/RestWebServices/Recall', 'cpsc_untrusted_api_url')
    query = parse_qs(u.query)
    require(set(query) == {'format', 'RecallDateStart', 'RecallDateEnd'}
            and query['format'] == ['json'] and all(len(v) == 1 for v in query.values()),
            'cpsc_unexpected_or_projected_query')
    scope = record.get('payload', {}).get('scope', {})
    start, end = query['RecallDateStart'][0], query['RecallDateEnd'][0]
    try:
        end_exclusive = (date.fromisoformat(end) + timedelta(days=1)).isoformat()
        date.fromisoformat(start)
    except ValueError:
        raise ProviderError('cpsc_invalid_query_dates') from None
    require(scope.get('start') == start and scope.get('end') == end_exclusive,
            'cpsc_window_mismatch')
    data = record.get('payload', {}).get('data')
    require(isinstance(data, dict) and str(data.get('RecallID')) == record.get('source_record_id'),
            'cpsc_identity_mismatch')
    rows = json_body(body)
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows), 'cpsc_original_not_recall_list')
    matches = [r for r in rows if r.get('RecallID') == data.get('RecallID')]
    require(len(matches) == 1 and matches[0] == data, 'cpsc_original_row_mismatch')
    day = str(data.get('RecallDate', ''))[:10]
    require(start <= day <= end and (record.get('event_at') or {}).get('value') == day,
            'cpsc_recall_date_mismatch')
    require(bool(data.get('RecallNumber') and data.get('Title') and data.get('Description'))
            and isinstance(data.get('Products'), list) and bool(data['Products']), 'cpsc_recall_content_missing')
    require(record.get('source_url') == (data.get('URL') or url), 'cpsc_recall_url_mismatch')
    return {'provider': 'CPSC recalls', 'record_type': 'product_recall', 'recall_id': str(data['RecallID']),
            'scope': 'Entire returned recall record; no claim of all incidents, downloaded images or historical vintages.'}


def mlperf(body, record, url):
    data = record.get('payload', {}).get('data', {})
    repo, commit = data.get('repository', ''), data.get('commit', '')
    require(isinstance(repo, str) and re.fullmatch(r'mlcommons/inference_results_v[0-9]+\.[0-9]+', repo),
            'mlperf_untrusted_repository')
    require(isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{40}', commit), 'mlperf_unpinned_commit')
    u = urlsplit(url)
    require(u.scheme == 'https' and not u.fragment and (not u.query or
            (u.netloc == 'api.github.com' and parse_qs(u.query) == {'recursive': ['1']})),
            'mlperf_untrusted_artifact_url')
    if 'result' in data:
        path = data.get('summary_file') or unquote(u.path).rsplit('/', 1)[-1]
        require(path in ('summary_results.json', 'summary.csv')
                and u.netloc == 'raw.githubusercontent.com' and unquote(u.path) == '/' + repo + '/' + commit + '/' + path,
                'mlperf_summary_not_commit_pinned')
        rows = json_body(body) if path.endswith('.json') else list(csv.DictReader(io.StringIO(body.decode('utf-8-sig'))))
        row = data['result']
        require(isinstance(row, dict) and isinstance(rows, list) and row in rows, 'mlperf_original_result_mismatch')
        identities = {repo + ':' + digest({k: row.get(k) for k in fields})
                      for fields in (IDENTITY_FIELDS, LEGACY_IDENTITY_FIELDS)}
        require(record.get('source_record_id') in identities, 'mlperf_result_identity_mismatch')
        require(record.get('source_url') == url, 'mlperf_result_url_mismatch')
        require(bool(row.get('Scenario') and (row.get('Model') or row.get('MlperfModel')))
                and any(row.get(k) is not None and row.get(k) != '' for k in ('Result', 'Performance_Result')),
                'mlperf_result_fields_missing')
        return {'provider': 'MLCommons MLPerf', 'record_type': 'benchmark_result', 'repository': repo,
                'commit': commit, 'scope': 'Exact published summary row; supporting logs/configuration and comparability remain separate.'}
    path = data.get('path', '')
    require(isinstance(path, str) and path and not path.startswith('/') and '\\' not in path
            and all(p not in ('', '.', '..') for p in path.split('/')), 'mlperf_invalid_artifact_path')
    require(record.get('source_record_id') == repo + ':' + path, 'mlperf_artifact_identity_mismatch')
    if 'content' in data:
        require(u.netloc == 'raw.githubusercontent.com' and unquote(u.path) == '/' + repo + '/' + commit + '/' + path,
                'mlperf_original_not_commit_pinned')
        expected_url = 'https://raw.githubusercontent.com/' + repo + '/' + commit + '/' + path
        require(unquote(record.get('source_url', '')) == expected_url, 'mlperf_original_url_mismatch')
        try:
            original = json_body(body) if path.endswith('.json') else body.decode('utf-8')
        except UnicodeError:
            raise ProviderError('mlperf_invalid_original_text') from None
        require(original == data['content'] and bool(original), 'mlperf_original_content_mismatch')
        blob = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
        expected_blob = record['payload'].get('scope', {}).get('blob_sha')
        if expected_blob:
            require(blob == expected_blob, 'mlperf_git_blob_mismatch')
        return {'provider': 'MLCommons MLPerf', 'record_type': 'benchmark_supporting_artifact',
                'repository': repo, 'commit': commit, 'path': path, 'git_blob_sha': blob,
                'scope': 'Original supporting file; not an independent published benchmark result.'}
    # Git trees are verified inventory records, never benchmark measurements.
    prefix = '/repos/' + repo + '/git/trees/'
    require(u.netloc == 'api.github.com' and u.path.startswith(prefix), 'mlperf_inventory_original_missing')
    tree = json_body(body)
    require(isinstance(tree, dict) and tree.get('sha') == u.path[len(prefix):]
            and tree.get('truncated') is False and isinstance(tree.get('tree'), list), 'mlperf_incomplete_tree')
    scope = record.get('payload', {}).get('scope', {})
    relative = path
    if scope.get('tree_sha'):
        require(scope['tree_sha'] == tree['sha'] and scope.get('commit') == commit
                and scope.get('repository') == repo, 'mlperf_inventory_scope_mismatch')
        parent = scope.get('path', '')
        require(path.startswith(parent + '/'), 'mlperf_inventory_path_mismatch')
        relative = path[len(parent) + 1:]
    expected_type = 'tree' if data.get('artifact_kind') == 'tree' else 'blob'
    expected_sha = data.get('tree_sha') if expected_type == 'tree' else data.get('blob_sha')
    matches = [e for e in tree['tree'] if e.get('path') == relative and e.get('type') == expected_type]
    require(len(matches) == 1 and matches[0].get('sha') == expected_sha, 'mlperf_inventory_entry_mismatch')
    expected_link = 'https://github.com/' + repo + ('/tree/' if expected_type == 'tree' else '/blob/') + commit + '/' + path
    # Older child-tree records used /blob/ even for subdirectories.
    require(unquote(record.get('source_url', '')) in (expected_link, expected_link.replace('/tree/', '/blob/')),
            'mlperf_inventory_url_mismatch')
    return {'provider': 'MLCommons MLPerf', 'record_type': 'benchmark_artifact_inventory',
            'repository': repo, 'commit': commit, 'path': path, 'git_object_sha': expected_sha,
            'scope': 'Exact saved tree entry; referenced file contents and commit-to-tree lineage are separate.'}


def evidence(record, s3, bucket):
    from metadata_engine.evidence import RawFailure, object_bytes, s3_key
    source = record.get('source') or record.get('source_key')
    validator = {'mlperf_results': mlperf, 'cpsc_recalls': cpsc}[source]
    data = record.get('payload', {}).get('data', {})
    errors = []
    for ref in record.get('payload', {}).get('source_evidence', []):
        url = ref.get('source_url', '')
        u = urlsplit(url)
        if source == 'mlperf_results':
            if ('result' in data or 'content' in data) and u.netloc != 'raw.githubusercontent.com':
                continue
            if 'result' not in data and 'content' not in data and '/git/trees/' not in u.path:
                continue
        if not ref.get('sha256'):
            continue
        key = ref.get('key') or s3_key(ref.get('s3_uri', ''), bucket)
        key = key if key.startswith('research-data/') else 'research-data/' + key
        if not key.startswith('research-data/source_documents/' + source + '/'):
            continue
        body = object_bytes(s3, bucket, key, expected=ref['sha256'])
        try:
            validation = validator(body, record, url)
        except ProviderError as error:
            errors.append(str(error))
            continue
        return [{'artifact_kind': 'provider_record', 's3_uri': 's3://' + bucket + '/' + key,
                 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body), 'origin': 'first_party_source',
                 'source_url': url, 'retrieved_at': ref.get('retrieved_at'), 'validation': validation}]
    raise RawFailure(errors[0] if errors else source + '_matching_original_missing')
