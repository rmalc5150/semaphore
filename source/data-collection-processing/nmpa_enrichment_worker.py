"""S26 detail backfill, ongoing reconciliation, evidence-based events and completion email."""
import argparse
import copy
import fcntl
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json, write_checked
from disclosure_collection import get_bytes
from regulatory_collection import EvidenceClient, CompanyMatcher, SourceIssue, stamp
from research_contract import ROOT, digest, load_json, seal_record
from nmpa_enrichment import VERSION, structured_detail, valid_detail, inventory_snapshot, event_facts, significant
from nmpa_drug_trials import parse_detail_page, BASE_URL


def registry(path):
    db = sqlite3.connect(path)
    db.executescript('''
      CREATE TABLE IF NOT EXISTS batches (key TEXT PRIMARY KEY);
      CREATE TABLE IF NOT EXISTS trials (registration TEXT PRIMARY KEY, parent TEXT, first_seen TEXT,
        baseline TEXT, baseline_at TEXT, status TEXT DEFAULT 'pending', attempts INTEGER DEFAULT 0,
        retry_after TEXT DEFAULT '', checked_at TEXT DEFAULT '', manifest TEXT, output_batches TEXT, outcome TEXT);
      CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY);
      CREATE TABLE IF NOT EXISTS budget (day TEXT PRIMARY KEY, reserved INTEGER);
      CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY,value TEXT);
    ''')
    return db


def save_state(db, key, value):
    with db:
        db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (key, json.dumps(value)))


def discover(store, db, index_path, max_batches):
    with sqlite3.connect('file:' + str(index_path) + '?mode=ro', uri=True) as index:
        batches = index.execute("SELECT key,sha256,dataset,records FROM batches WHERE source='nmpa_trials' "
            "AND dataset IN ('registry_inventory','research_records') ORDER BY key").fetchall()
    pending = [b for b in batches if not db.execute('SELECT 1 FROM batches WHERE key=?', (b[0],)).fetchone()]
    for key, sha, dataset, count in pending[:max_batches]:
        raw = get_bytes(store, key, sha)
        rows = [json.loads(line) for line in raw.splitlines()]
        if len(rows) != count:
            raise ValueError('nmpa_input_count_mismatch')
        with db:
            for parent in rows:
                if parent['source'] != 'nmpa_trials' or parent['dataset'] != dataset:
                    raise ValueError('nmpa_input_scope_mismatch')
                if parent['payload'].get('enrichment_worker') == VERSION:
                    continue
                registration = parent['source_record_id']
                if not __import__('re').fullmatch(r'CTR20\d{6,}', registration):
                    continue
                at = parent['ingested_at']
                facts = inventory_snapshot(parent['payload']) if dataset == 'registry_inventory' else parent['payload']['data'].get('structured')
                if facts is None:
                    for ref in reversed(parent['payload'].get('source_evidence', [])):
                        url = urlsplit(ref['source_url'])
                        if 'searchlistdetail' in url.path and parse_qs(url.query).get('reg_no') == [registration]:
                            try:
                                facts = structured_detail(get_bytes(store, ref['key'], ref['sha256']).decode('utf-8'), registration)
                                break
                            except (SourceIssue, ValueError):
                                # Older runs attached cumulative page evidence.
                                # A failed/mismatched historical document must
                                # never seed another trial's change baseline.
                                parent['payload'].setdefault('enrichment_seed_warnings', []).append('saved_detail_unusable')
                old = db.execute('SELECT first_seen,baseline_at,status FROM trials WHERE registration=?', (registration,)).fetchone()
                if old is None:
                    db.execute('INSERT INTO trials(registration,parent,first_seen,baseline,baseline_at) VALUES (?,?,?,?,?)',
                               (registration, json.dumps(parent), at, json.dumps(facts), at))
                elif old[2] not in ('done', 'gap'):
                    if at < old[0]:
                        db.execute('UPDATE trials SET first_seen=? WHERE registration=?', (at, registration))
                    if facts is not None and at > old[1]:
                        db.execute('UPDATE trials SET parent=?,baseline=?,baseline_at=? WHERE registration=?',
                                   (json.dumps(parent), json.dumps(facts), at, registration))
            db.execute('INSERT INTO batches VALUES (?)', (key,))
    return max(0, len(pending) - max_batches)


def inventory_complete(store, db, config):
    head = json.loads(get_bytes(store, config['inventory_checkpoint']))
    if head['task']['source'] != 'nmpa_trials' or head['task']['dataset'] != 'registry_inventory':
        raise ValueError('nmpa_inventory_checkpoint_scope_mismatch')
    return bool(head['status'] == 'complete' and head['exhausted'] and all(
        db.execute('SELECT 1 FROM batches WHERE key=?', (b['key'],)).fetchone()
        for page in head['pages'] for b in page['batches']))


def snapshot_record(parent, run, facts, evidence, observed_at, config):
    names = facts.get('sponsors', [])
    candidates, sectors = CompanyMatcher(run.universe).match(names)
    disclosed = next((m['date'] for m in facts['milestones'] if m['kind'] == 'FIRST_PUBLIC_DISCLOSURE'), None)
    registration = facts['registration_number']
    data = {'registrationNumber': registration, 'structured': facts,
            'firstPublicDisclosureDate': disclosed,
            'inventory_prerequisite': {'record_id': parent['record_id'], 'observation_id': parent['observation_id']}}
    return seal_record({'document_type': 'collected_record', 'schema_version': '1.0',
        'source': 'nmpa_trials', 'dataset': 'research_records', 'source_record_id': registration,
        'source_record_id_basis': 'provider', 'source_url': BASE_URL + 'clinicaltrials.searchlistdetail.dhtml?reg_no=' + registration,
        'universe_version': run.universe['universe_version'], 'company_ids': [], 'listing_ids': [], 'product_ids': [], 'person_ids': [],
        'entity_match_status': 'unresolved', 'event_at': stamp(disclosed), 'available_at': None, 'source_updated_at': None,
        'ingested_at': observed_at, 'availability_basis': 'unknown', 'availability_evidence': [], 'run_id': run.run_id,
        'payload': {'provider_id': registration, 'record_type': 'clinical_trial', 'data': data,
            'title': facts.get('public_title') or facts.get('professional_title') or facts.get('drug_name'), 'company_names': names, 'candidate_company_ids': candidates,
            'candidate_sector_ids': sectors, 'company_match_basis': 'unverified_name', 'source_evidence': evidence,
            'enrichment_worker': VERSION, 'enrichment_job_id': config['job_id'],
            'date_basis': 'first_public_disclosure_date',
            'coverage_note': 'Current source trial details. Observed changes have observation intervals, not inferred milestone dates. No approval, trial success or cross-country identity inferred.'}})


def output_rows(store, manifest):
    doc = json.loads(get_bytes(store, manifest))
    refs = [b for p in doc['pages'] for b in p['batches']]
    rows = [json.loads(line) for b in refs for line in get_bytes(store, b['key'], b['sha256']).splitlines()]
    return rows, refs


def capture(store, settings, universe, taxonomy, config, db, client, trial, cycle):
    registration, parent_json, first_seen, baseline_json, baseline_at, attempts = trial
    parent, previous = json.loads(parent_json), json.loads(baseline_json)
    spec = task_spec('nmpa_trials', 'research_records', 'historical', config['window_start'], config['scope_end'],
        {'enrichment_job_id': config['job_id'], 'registration': registration, 'cycle': cycle}, VERSION, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
    except AlreadyComplete as exc:
        records, refs = output_rows(store, str(exc))
        return records, refs, str(exc)
    if run.exhausted:
        manifest = run.finish('complete')
        records, refs = output_rows(store, manifest)
        return records, refs, manifest
    try:
        before = len(client.evidence)
        url = BASE_URL + 'clinicaltrials.searchlistdetail.dhtml?reg_no=' + registration
        document = client.rendered(url, pending_validator=lambda doc: valid_detail(doc, registration))
        facts = structured_detail(document, registration)
        if not facts.get('drug_name') or not facts.get('status'):
            raise SourceIssue('nmpa_detail_identity_fields_missing', True)
        at = now()
        evidence = client.evidence[before:]
        snapshot = snapshot_record(parent, run, facts, evidence, at, config)
        snapshot['payload']['data']['fields'] = parse_detail_page(document)
        snapshot = seal_record(snapshot)
        events = event_facts(registration, previous, facts, baseline_at, at)
        events += event_facts(registration, None, facts, None, first_seen)[:1]
        records = [snapshot]
        prior_evidence = parent['payload'].get('source_evidence', [])
        for event in {e['id']: e for e in events}.values():
            if db.execute('SELECT 1 FROM events WHERE id=?', (event['id'],)).fetchone():
                continue
            value = copy.deepcopy(snapshot)
            value['source_record_id'] = event['id']
            value['source_record_id_basis'] = 'documented_composite'
            value['event_at'] = stamp(event['date']) if len(event['date']) == 10 else {
                'value': event['date'], 'precision': 'microsecond', 'source_timezone': 'UTC'}
            value['payload'] = {**value['payload'], 'record_type': 'regulatory_event',
                'date_basis': event['date_basis'], 'data': {'registrationNumber': registration, **event},
                'source_evidence': prior_evidence + evidence}
            records.append(seal_record(value))
        run.commit_page(records, exhausted=True)
        manifest = run.finish('complete', expected_records=len(records))
        _, refs = output_rows(store, manifest)
        return records, refs, manifest
    except (Exception, KeyboardInterrupt):
        run.finish('partial', 'nmpa_detail_retry_required')
        raise


def reserve(db, config):
    day = now()[:10]
    with db:
        db.execute('INSERT OR IGNORE INTO budget VALUES (?,0)', (day,))
        used = db.execute('SELECT reserved FROM budget WHERE day=?', (day,)).fetchone()[0]
        if used + 4 > config['max_provider_requests_per_day']:
            return False
        # EvidenceClient performs at most four provider attempts per detail call.
        db.execute('UPDATE budget SET reserved=reserved+4 WHERE day=?', (day,))
    return True


def notify(store, db, config, state, sns, athena):
    if state.get('notification_message_id') or not state['inventory_complete'] or state['remaining_input_batches'] or state['pending_trials']:
        return state
    refs = [r for (value,) in db.execute("SELECT output_batches FROM trials WHERE status='done'") for r in json.loads(value)]
    with sqlite3.connect('file:' + str(ROOT / 'committed-athena-index.sqlite3') + '?mode=ro', uri=True) as index:
        if not all(index.execute('SELECT 1 FROM verified_batches WHERE key=?', (b['key'],)).fetchone() for b in refs):
            state['status'] = 'awaiting_athena_publication'
            return state
    from committed_data_athena import query
    if not db.execute('SELECT count(*) FROM trials').fetchone()[0]:
        raise ValueError('nmpa_empty_backfill_scope')
    result = query(athena, "SELECT count(*) FROM optima_collected_data.observations WHERE source='nmpa_trials' AND dataset='research_records' AND "
        "json_extract_scalar(payload_json,'$.enrichment_job_id')='" + config['job_id'] + "'")
    # Before notification reconciliation cycles are held back; each completed
    # trial's initial committed output contributes exactly these rows.
    expected = sum(b['records'] for b in refs)
    if int(result['rows'][0][0]) != expected:
        raise ValueError('nmpa_athena_count_mismatch')
    subscriptions = [s for p in sns.get_paginator('list_subscriptions_by_topic').paginate(TopicArn=config['email_topic_arn']) for s in p['Subscriptions']]
    if not subscriptions or not all(s['Protocol'] == 'email' and s['Endpoint'] == config['email_recipient'] and s['SubscriptionArn'].startswith('arn:') for s in subscriptions):
        raise ValueError('nmpa_email_subscription_mismatch')
    gaps = db.execute("SELECT count(*) FROM trials WHERE status='gap' OR outcome='partial_fields'").fetchone()[0]
    state['trials_with_missing_core_fields'] = db.execute("SELECT count(*) FROM trials WHERE outcome='partial_fields'").fetchone()[0]
    state['gap_reason_counts'] = dict(db.execute("SELECT outcome,count(*) FROM trials WHERE status='gap' OR outcome='partial_fields' GROUP BY outcome").fetchall())
    state['sample_gaps'] = [dict(zip(('registration','reason'),row)) for row in
        db.execute("SELECT registration,outcome FROM trials WHERE status='gap' OR outcome='partial_fields' ORDER BY registration LIMIT 20")]
    state['gap_receipts_prefix'] = 'operations/nmpa/enrichment/' + config['job_id'] + '/gaps/'
    state.update(status='finished_with_gaps' if gaps else 'complete', athena_verification=result,
                 verified_output_records=expected, finished_at=now())
    response = sns.publish(TopicArn=config['email_topic_arn'], Subject='S26 NMPA enrichment backfill finished' + (' - gaps recorded' if gaps else ' - verified'),
        Message='The S26 trial detail backfill has finished processing the completed observed registry inventory.\n\n' + json.dumps(state,ensure_ascii=False,indent=2) +
        '\n\nUse the updated S26 detail/event queries in ENTITY_DISCOVERY_ROLLOUT_PLAN.md#sql-checks. Inventory rows remain discovery evidence. '
        'FIRST_OBSERVED and TRIAL_CHANGE_OBSERVED are observation events, not inferred trial-start or completion dates. '
        'Explicit dated milestones retain their source labels. Names and drug aliases remain unverified entity candidates. '
        'Unretrievable records are explicit gaps, not enriched trials; listings are not a transactionally frozen global snapshot.')
    state.update(notification_message_id=response['MessageId'], notified_at=now())
    return state


def execute(config):
    import boto3
    settings = StorageSettings.load(ROOT / config['storage_config'])
    store = settings.store()
    prefix = 'operations/nmpa/enrichment/' + config['job_id']
    write_checked(store, prefix + '/config.json', (json.dumps(config,sort_keys=True)+'\n').encode())
    with registry(ROOT / (config['job_id'] + '.sqlite3')) as db:
        old = db.execute("SELECT value FROM state WHERE key='receipt'").fetchone()
        old = json.loads(old[0]) if old else {}
        remaining = discover(store, db, ROOT / 'committed-athena-index.sqlite3', config['max_batches_per_invocation'])
        client = EvidenceClient(store, 'nmpa_trials')
        clause = "status IN ('pending','retry')"
        if old.get('notification_message_id'):
            due = (datetime.now(timezone.utc) - timedelta(days=config['revisit_days'])).isoformat().replace('+00:00','Z')
            clause += " OR (status IN ('done','gap') AND checked_at<'" + due + "')"
        priorities = config.get('priority_ids', [])
        order = 'CASE WHEN registration IN (' + ','.join('?' for _ in priorities) + ') THEN 0 ELSE 1 END,' if priorities else ''
        rows = db.execute('SELECT registration,parent,first_seen,baseline,baseline_at,attempts FROM trials WHERE (' + clause +
            ') AND retry_after<=? ORDER BY ' + order + 'checked_at,registration LIMIT ?', (now(), *priorities, config['max_trials_per_invocation'])).fetchall()
        initial = {**old,'job_id':config['job_id'],'status':'capturing_details','updated_at':now(),
            'known_trials':db.execute('SELECT count(*) FROM trials').fetchone()[0],
            'remaining_input_batches':remaining,'counts':dict(db.execute('SELECT status,count(*) FROM trials GROUP BY status').fetchall())}
        (ROOT/'reports'/(config['job_id']+'-latest.json')).write_text(json.dumps(initial,ensure_ascii=False,indent=2)+'\n')
        existing = store.get(prefix+'/state.json')
        write_json(store,prefix+'/state.json',initial,existing.token if existing else None)
        for row in rows:
            if not reserve(db, config):
                break
            registration = row[0]
            cycle = 'baseline' if not old.get('notification_message_id') else now()[:10]
            retry = (datetime.now(timezone.utc) + timedelta(minutes=config['retry_minutes'])).isoformat().replace('+00:00','Z')
            with db:
                db.execute('UPDATE trials SET retry_after=? WHERE registration=?', (retry, registration))
            try:
                records, refs, manifest = capture(store, settings, load_json(ROOT / config['universe']),
                    load_json(ROOT / config['taxonomy']), config, db, client, row, cycle)
            except SourceIssue as exc:
                if exc.code == 'scrape_gateway_http_429':
                    print(json.dumps({'status':'deferred','reason':exc.code}),flush=True)
                    break
                attempts = row[5] + 1
                status = 'gap' if attempts >= config['max_attempts'] else 'retry'
                with db:
                    db.execute('UPDATE trials SET status=?,attempts=?,outcome=?,checked_at=? WHERE registration=?', (status, attempts, exc.code,now(),registration))
                write_json(store,prefix + '/gaps/' + registration + '/' + str(attempts) + '.json',
                    {'registration':registration,'status':status,'reason':exc.code,'at':now()})
                print(json.dumps({'registration':registration,'status':status,'reason':exc.code}),flush=True)
                continue
            snapshot = records[0]
            outcome = 'partial_fields' if snapshot['payload']['data']['structured']['missing_core_fields'] else 'enriched'
            with db:
                db.execute("UPDATE trials SET status='done',attempts=0,retry_after='',checked_at=?,baseline=?,baseline_at=?,manifest=?,output_batches=?,outcome=? WHERE registration=?",
                    (snapshot['ingested_at'],json.dumps(snapshot['payload']['data']['structured']),snapshot['ingested_at'],manifest,json.dumps(refs),outcome,registration))
                for record in records[1:]:
                    db.execute('INSERT OR IGNORE INTO events VALUES (?)',(record['source_record_id'],))
            print(json.dumps({'registration':registration,'status':'enriched','events':len(records)-1}),flush=True)
        state = {**old,'job_id':config['job_id'],'status':'reconciling' if old.get('notification_message_id') else 'running',
            'updated_at':now(),'inventory_complete':inventory_complete(store,db,config),'remaining_input_batches':remaining,
            'pending_trials':db.execute("SELECT count(*) FROM trials WHERE status NOT IN ('done','gap')").fetchone()[0],
            'counts':dict(db.execute('SELECT status,count(*) FROM trials GROUP BY status').fetchall()),
            'events':db.execute('SELECT count(*) FROM events').fetchone()[0], 'scope_note':config['scope_note']}
        state = notify(store,db,config,state,boto3.client('sns',region_name=settings.region),boto3.client('athena',region_name=settings.region))
        save_state(db,'receipt',state)
        existing = store.get(prefix+'/state.json')
        write_json(store,prefix+'/state.json',state,existing.token if existing else None)
        (ROOT/'reports'/(config['job_id']+'-latest.json')).write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='config/nmpa-enrichment-backfill.json')
    args = parser.parse_args()
    with (ROOT/'.nmpa-enrichment.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return 2
        print(json.dumps(execute(load_json(ROOT/args.config)),ensure_ascii=False),flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
