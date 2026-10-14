"""Finite Finlight archive with receipt-verified downgrade notification."""
from datetime import date, timedelta
import hashlib
import json

from collection_operations import load_stored
from collection_storage import now, write_json
from news_collection import NewsClient, targets
from research_contract import ROOT, digest, load_json


def setup():
    control = load_json(ROOT / 'config/finlight-backfill.json')
    config = load_json(ROOT / control['collection_config'])
    identity = digest({'collection': config, 'start': control['start'], 'end': control['end_exclusive'],
                       'universe': digest(load_json(ROOT / config['universe'])),
                       'taxonomy': digest(load_json(ROOT / config['taxonomy']))})
    return control, config, 'operations/news/finlight-backfill/' + identity


def collect_archive(runner, api_key):
    control, config, prefix = setup()
    if not control['enabled']:
        return {'status': 'disabled'}
    key = prefix + '/collection.json'
    state, token = load_stored(runner.store, key)
    state = state or {'next_date': control['start']}
    client = NewsClient(runner.store, 'finlight', api_key,
                        control['max_requests_per_day'], control['max_requests_per_invocation'])
    for _ in range(control['max_days_per_invocation']):
        day = date.fromisoformat(state['next_date'])
        if day >= date.fromisoformat(control['end_exclusive']):
            break
        result = runner.window('finlight', day, 'historical', client, config)
        state.update(last_result=result, updated_at=now())
        if result['status'] == 'complete':
            state['next_date'] = str(day + timedelta(days=1))
        token = write_json(runner.store, key, state, token)
        if result['status'] != 'complete':
            break
    return state


def check_completion(runner, sns, email_topic, today=None):
    """Advance only through matching, hashed Athena verification receipts.

    Called under the news publication lock; retries send failures next cycle.
    SNS acceptance followed by a failed state write can cause a duplicate email.
    """
    control, config, prefix = setup()
    if not control['enabled']:
        return {'status': 'disabled'}
    key = prefix + '/publication.json'
    state, token = load_stored(runner.store, key)
    state = state or {'next_date': control['start']}
    if state.get('notification_message_id'):
        return state
    collection, _ = load_stored(runner.store, prefix + '/collection.json')
    publication_config = load_json(ROOT / 'config/news-athena.json')
    expected_scope = targets(config, runner.universe, [], [])
    for _ in range(32):
        day = date.fromisoformat(state['next_date'])
        if (not collection or day >= date.fromisoformat(collection['next_date'])
                or day >= date.fromisoformat(control['end_exclusive'])):
            break
        window_id = digest({'provider': 'finlight', 'date': str(day), 'mode': 'historical',
                            'universe': digest(runner.universe), 'targets': expected_scope})
        queue, _ = load_stored(runner.store, 'operations/news/publication-queue/' + window_id + '.json')
        receipt, _ = load_stored(runner.store, 'operations/news/publication-receipts/' + window_id + '.json')
        if not queue or not receipt or receipt.get('status') != 'verified':
            break
        source_hash = digest({'manifests': queue['manifests'], 'config': publication_config,
                              'curation_version': 'window-publication-1.0'})
        if receipt.get('source_hash') != source_hash:
            break
        # A refreshed queue must still belong to this exact archive configuration.
        scopes = set()
        for manifest_key in queue['manifests']:
            manifest, _ = load_stored(runner.store, manifest_key)
            task = (manifest or {}).get('task', {})
            scope = task.get('scope', {})
            if (not manifest or manifest.get('status') != 'complete' or not manifest.get('exhausted')
                    or task.get('source') != 'finlight' or task.get('mode') != 'historical'
                    or task.get('window', {}).get('start', '')[:10] != str(day)
                    or task.get('window', {}).get('end', '')[:10] != str(day + timedelta(days=1))
                    or scope.get('configuration_hash') != digest(config)):
                return {'status': 'scope_mismatch', 'date': str(day)}
            scopes.add((scope['target']['name'], scope['language']))
        expected = {(t['name'], lang) for t in expected_scope for lang in config['providers']['finlight']['languages']}
        if scopes != expected:
            return {'status': 'scope_incomplete', 'date': str(day)}
        obj = runner.store.get(receipt['verification_key'])
        if obj is None or hashlib.sha256(obj.body).hexdigest() != receipt['verification_sha256']:
            return {'status': 'invalid_verification', 'date': str(day)}
        verification = json.loads(obj.body)
        if (verification.get('status') != 'verified' or verification.get('window_id') != window_id
                or verification.get('release_id') != receipt.get('release_id')):
            return {'status': 'invalid_verification', 'date': str(day)}
        state.update(next_date=str(day + timedelta(days=1)), updated_at=now())
        token = write_json(runner.store, key, state, token)
    today = today or date.fromisoformat(now()[:10])
    daily, _ = load_stored(runner.store, runner.prefix + '/finlight/daily.json')
    ready = (state['next_date'] >= control['end_exclusive'] and collection
             and collection['next_date'] >= control['end_exclusive'] and daily
             and daily['next_date'] >= str(today))
    state['status'] = 'ready_to_downgrade' if ready else 'incomplete'
    if ready and control['notify_when_verified'] and email_topic:
        body = (f"Finlight historical collection and Athena verification are complete for "
                f"{control['start']} through {control['end_exclusive']} (exclusive), for the four "
                "configured sector searches in English and Chinese. Daily capture is caught up. "
                "You can now move the subscription back to Pro Light. This is scoped search "
                "completion, not an exhaustive worldwide news archive. Downgrading limits future "
                "historical re-queries and may remove sentiment access. Your subscription has not "
                "been changed automatically.")
        response = sns.publish(TopicArn=email_topic, Subject='Finlight backfill verified — ready for Light', Message=body)
        state.update(notification_message_id=response['MessageId'], notified_at=now())
    write_json(runner.store, key, state, token)
    return state
