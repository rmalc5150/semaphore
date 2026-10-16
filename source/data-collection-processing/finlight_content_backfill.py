#!/usr/bin/env python3
"""Enrich saved Finlight observations; one archive discovery job, one content worker."""
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import sqlite3

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json
from collection_operations import load_stored
from disclosure_collection import get_bytes
from finlight_content import Capture, VERSION, apply
from regulatory_collection import SourceIssue, require
from research_contract import ROOT, digest, load_json, parse_instant, seal_record


def save(store, key, value):
    obj = store.get(key)
    write_json(store, key, value, obj.token if obj else None)


def registry(path):
    db = sqlite3.connect(path)
    db.executescript('''CREATE TABLE IF NOT EXISTS batches (key TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS articles (url TEXT PRIMARY KEY, parent TEXT, lineage TEXT,
            status TEXT DEFAULT 'pending', attempts INTEGER DEFAULT 0, retry_after TEXT DEFAULT '', manifest TEXT);''')
    return db


def verify_capture(store, capture):
    require(capture['status'] == 'captured', 'fulltext_not_captured')
    body = json.loads(get_bytes(store, capture['reference']['key'], capture['reference']['sha256']))
    require(body['text'] and hashlib.sha256(body['text'].encode()).hexdigest() == capture['text_sha256'], 'fulltext_hash_mismatch')
    for ref in capture['source_evidence']:
        get_bytes(store, ref['key'], ref['sha256'])
    return len(body['text'])


def discover(store, db, config, index_path, max_batches=100):
    source = config.get('provider', 'finlight')
    version = __import__(source + '_content').VERSION
    index = sqlite3.connect('file:' + str(index_path) + '?mode=ro', uri=True)
    batches = index.execute("SELECT key,sha256 FROM batches WHERE source=? AND dataset=? ORDER BY key", (source, config.get('dataset','news_articles'))).fetchall()
    index.close()
    remaining = 0
    processed = 0
    for key, sha in batches:
        if db.execute('SELECT 1 FROM batches WHERE key=?', (key,)).fetchone():
            continue
        if processed >= max_batches:
            remaining += 1
            continue
        raw = get_bytes(store, key, sha)
        for line in raw.splitlines():
            parent = json.loads(line)
            require(parent['source'] == source, 'fulltext_parent_source_mismatch')
            p = parent['payload']
            published = parent['ingested_at'] if config.get('date_basis') == 'snapshot_ingestion' else parent['event_at']['value'][:10]
            lower = config.get('snapshot_start', config['start'])
            upper = config.get('snapshot_cutoff', config['end_exclusive'])
            if not lower <= published < upper:
                continue
            # New collection already enriches its own observations. Verify its
            # body, rather than create another observation for that article.
            full = p.get('full_text', {})
            already = full.get('status') == 'captured' and full.get('version') == version
            if already:
                verify_capture(store, full)
            url = p['data']['link' if source == 'finlight' else 'url']
            old = db.execute('SELECT parent,status FROM articles WHERE url=?', (url,)).fetchone()
            lineage = {'batch': key, 'batch_sha256': sha, 'observation_id': parent['observation_id'],
                'record_id': parent['record_id']}
            if old is None:
                db.execute('INSERT INTO articles(url,parent,lineage,status) VALUES (?,?,?,?)',
                    (url, json.dumps(parent), json.dumps(lineage), 'captured' if already else 'pending'))
            elif already:
                db.execute("UPDATE articles SET status='captured' WHERE url=?", (url,))
            elif old[1] != 'captured' and parent['ingested_at'] > json.loads(old[0])['ingested_at']:
                db.execute('UPDATE articles SET parent=?,lineage=? WHERE url=?', (json.dumps(parent), json.dumps(lineage), url))
        db.execute('INSERT INTO batches VALUES (?)', (key,))
        db.commit()
        processed += 1
    return remaining


def enrich_one(store, settings, universe, taxonomy, config, parent, lineage, capture_client, attempt):
    source = config.get('provider', 'finlight')
    version = __import__(source + '_content').VERSION
    spec = task_spec(source, config.get('dataset', 'news_articles'), 'historical', config['start'] + 'T00:00:00Z',
        config['end_exclusive'] + 'T00:00:00Z', {'full_text_pipeline_version': version,
        'parent_observation_id': parent['observation_id'], 'article_url': parent['source_url'], 'attempt': attempt},
        version, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
    except AlreadyComplete as exc:
        manifest = json.loads(get_bytes(store, str(exc)))
        batch = manifest['pages'][0]['batches'][0]
        record = json.loads(get_bytes(store, batch['key'], batch['sha256']).splitlines()[0])
        return record['payload']['full_text'], str(exc)
    try:
        capture = capture_client.get(parent['payload']['data'])
        enriched = apply(parent, capture, store)
        enriched.update(run_id=run.run_id, ingested_at=now())
        enriched['payload']['full_text_backfill'] = {'prerequisite': lineage, 'version': version}
        enriched = seal_record(enriched)
        run.commit_page([enriched], exhausted=True)
        manifest = run.finish('complete', expected_records=1)
        if capture['status'] == 'captured':
            verify_capture(store, capture)
        return capture, manifest
    except (Exception, KeyboardInterrupt):
        run.finish('partial', 'fulltext_retry_required')
        raise


def archive_ready(store, config):
    if config.get('provider') == 'people_rss':
        from people_content_backfill import archive_ready as ready
        return ready(store, config)
    if config.get('provider') == 'marketaux':
        from marketaux_content_backfill import archive_ready as ready
        return ready(store, config)
    from finlight_backfill import setup
    from news_operations import NewsOperations
    control, _, prefix = setup()
    collected, _ = load_stored(store, prefix + '/collection.json')
    published, _ = load_stored(store, prefix + '/publication.json')
    settings = StorageSettings.load(ROOT / config['storage_config'])
    runner = NewsOperations(store, settings, load_json(ROOT / 'config/news-operations.json'))
    daily, _ = load_stored(store, runner.prefix + '/finlight/daily.json')
    catalog = load_json(ROOT / 'reports/committed-athena-latest.json')
    ready = bool(collected and published and daily and
        collected['next_date'] >= control['end_exclusive'] and published['next_date'] >= control['end_exclusive'] and
        daily['next_date'] >= config['end_exclusive'] and catalog.get('status') == 'verified')
    if ready:
        last_capture = max(parse_instant(s['updated_at']) for s in (collected, daily))
        ready = parse_instant(catalog['started_at']) >= last_capture
    return ready


def run(store, settings, config, universe, taxonomy, provider, sns, db, index_path):
    source = config.get('provider', 'finlight')
    module = __import__(source + '_content')
    prefix = 'operations/news/fulltext/backfill/' + digest({'config': config, 'version': module.VERSION})
    state_key = prefix + '/state.json'
    previous, _ = load_stored(store, state_key)
    if previous and previous.get('notification_message_id'):
        return previous
    remaining_batches = discover(store, db, config, index_path, config['max_batches_per_invocation'])
    capture_client = module.Capture(store, provider, config['max_articles_per_invocation'])
    rows = db.execute("SELECT url,parent,lineage,attempts FROM articles WHERE status!='captured' AND status!='gap_final' AND retry_after<=? LIMIT ?",
        (now(), config['max_articles_per_invocation'])).fetchall()
    for url, parent_json, lineage_json, attempts in rows:
        try:
            capture, manifest = enrich_one(store, settings, universe, taxonomy, config,
                json.loads(parent_json), json.loads(lineage_json), capture_client, attempts + 1)
        except SourceIssue as exc:
            if exc.partial:
                break
            raise
        good = capture['status'] == 'captured'
        status = 'captured' if good else 'gap_final' if attempts + 1 >= config['max_attempts'] else 'gap_retry'
        retry = '' if good else (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat().replace('+00:00', 'Z')
        db.execute('UPDATE articles SET status=?,attempts=?,retry_after=?,manifest=? WHERE url=?',
            (status, attempts + 1, retry, manifest, url))
        db.commit()
        save(store, prefix + '/articles/' + digest(url) + '.json', {'article_url': url, 'status': status,
            'manifest': manifest, 'capture': capture, 'attempts': attempts + 1, 'verified_at': now()})
        print(json.dumps({'stage': 'article_content', 'status': status, 'article_id': digest(url),
            'text_characters': capture['text_characters']}), flush=True)
    counts = dict(db.execute('SELECT status,count(*) FROM articles GROUP BY status').fetchall())
    pending = counts.get('pending', 0) + counts.get('gap_retry', 0)
    ready = remaining_batches == 0 and not pending and archive_ready(store, config)
    state = {'status': 'finished_with_gaps' if ready and counts.get('gap_final') else 'complete' if ready else 'running',
        'counts': counts, 'remaining_catalog_batches': remaining_batches, 'updated_at': now(), 'scope_note': config['scope_note']}
    save(store, state_key, state)
    if ready and config.get('notify_when_verified', True):
        subscriptions = [s for p in sns.get_paginator('list_subscriptions_by_topic').paginate(TopicArn=config['email_topic_arn'])
            for s in p['Subscriptions']]
        require(subscriptions and all(s['Protocol'] == 'email' and s['Endpoint'] == config['email_recipient'] and
            s['SubscriptionArn'].startswith('arn:') for s in subscriptions), 'fulltext_email_subscription_mismatch')
        message = sns.publish(TopicArn=config['email_topic_arn'], Subject=config.get('email_label', source.title()) + ' full-article backfill finished — gaps recorded' if counts.get('gap_final') else config.get('email_label', source.title()) + ' full-article backfill complete — verified',
            Message=state['status'] + '\n\n' + json.dumps(counts, indent=2) + '\n\n' + config['scope_note'] +
            '\nAll configured discovery and publication completion checks passed.\nReceipt: ' + state_key)
        state.update(notification_message_id=message['MessageId'], notified_at=now())
        save(store, state_key, state)
        if source != 'finlight':
            return state
        from finlight_backfill import setup
        _, _, archive_prefix = setup()
        key = archive_prefix + '/publication.json'
        publication, token = load_stored(store, key)
        if publication:
            publication['full_text_notification_message_id'] = message['MessageId']
            write_json(store, key, publication, token)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/finlight-content-backfill.json')
    args = parser.parse_args()
    config = load_json(ROOT / args.config)
    # The discovery timer starts around minute 05. Leave it an admission
    # window; this worker's service is bounded to four minutes per run.
    if 1 <= datetime.now(timezone.utc).minute <= 9:
        print(json.dumps({'status': 'partial', 'reason': 'daily_news_capture_priority'}))
        return 2
    with (ROOT / '.news-collection.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status': 'partial', 'reason': 'runner_already_active'}))
            return 2
        import boto3
        from news_collection import NewsClient
        settings = StorageSettings.load(ROOT / config['storage_config'])
        daily = load_json(ROOT / 'config/news-collection.json')
        source = config.get('provider', 'finlight')
        if source == 'people_rss':
            from people_content_backfill import execute
            return execute(config, settings, daily)
        keys = json.loads(boto3.client('secretsmanager', region_name=settings.region).get_secret_value(SecretId=daily['secret_id'])['SecretString'])
        provider = NewsClient(settings.store(), source, keys[daily['providers'][source]['secret_field']],
            config['max_provider_requests_per_day'], config['max_articles_per_invocation'])
        provider.fulltext_api_reserve = 0
        with registry(ROOT / (source + '-content-backfill-' + digest(config)[:16] + '.sqlite3')) as db:
            result = run(provider.store, settings, config, load_json(ROOT / daily['universe']),
                load_json(ROOT / daily['taxonomy']), provider, boto3.client('sns', region_name=settings.region),
                db, ROOT / 'committed-athena-index.sqlite3')
        print(json.dumps(result), flush=True)
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
