"""Saved RSS full bodies and their existing personnel archive projection."""
import fcntl
import json
import sqlite3
from collection_operations import load_stored
from collection_storage import now
from research_contract import ROOT, digest, load_json, parse_instant


def registry_path(config):
    return ROOT / ('people_rss-content-backfill-' + digest(config)[:16] + '.sqlite3')


def archive_ready(store, config):
    catalog = load_json(ROOT / 'reports/committed-athena-latest.json')
    if catalog.get('status') != 'verified' or parse_instant(catalog['started_at']) < parse_instant(config['snapshot_cutoff']):
        return False
    path = registry_path(config)
    if not path.exists():
        return False
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS archive_receipts (manifest TEXT PRIMARY KEY, checked_at TEXT)')
        missing = db.execute("SELECT count(*) FROM articles a LEFT JOIN archive_receipts r ON a.manifest=r.manifest WHERE a.manifest IS NOT NULL AND r.manifest IS NULL").fetchone()[0]
        latest = db.execute('SELECT max(checked_at) FROM archive_receipts').fetchone()[0]
    return not missing and (not latest or parse_instant(catalog['started_at']) >= parse_instant(latest))


def propagate(store, settings, db, limit=5):
    from finlight_content_backfill import save
    from personnel_archive import collect, VERSION
    db.execute('CREATE TABLE IF NOT EXISTS archive_receipts (manifest TEXT PRIMARY KEY, checked_at TEXT)')
    db.commit()
    with (ROOT / '.personnel-archive.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        rows = db.execute('SELECT DISTINCT a.manifest FROM articles a LEFT JOIN archive_receipts r ON a.manifest=r.manifest WHERE a.manifest IS NOT NULL AND r.manifest IS NULL LIMIT ?', (limit,)).fetchall()
        for (manifest,) in rows:
            key = 'operations/personnel-archive/processed/' + digest([VERSION,manifest]) + '.json'
            receipt, _ = load_stored(store,key)
            if not receipt:
                result = collect(store,settings,manifest)
                if result['status'] != 'complete':
                    continue
                receipt = {**result,'input_manifest':manifest,'checked_at':now()}
                save(store,key,receipt)
            db.execute('INSERT OR REPLACE INTO archive_receipts VALUES (?,?)',(manifest,receipt['checked_at']))
            db.commit()


def execute(config, settings, daily):
    import boto3
    from finlight_content_backfill import registry, run
    store = settings.store()
    with registry(registry_path(config)) as db:
        result = run(store,settings,config,load_json(ROOT/daily['universe']),load_json(ROOT/daily['taxonomy']),
            None,boto3.client('sns',region_name=settings.region),db,ROOT/'committed-athena-index.sqlite3')
        propagate(store,settings,db)
    # Keep retrying new snapshots after the finite historical completion email.
    # A fixed registry retains retry state across date changes.
    maintenance = dict(config, snapshot_start=config['snapshot_cutoff'],
        snapshot_cutoff='9999-01-01T00:00:00Z', notify_when_verified=False,
        maintenance=True)
    with registry(registry_path(maintenance)) as db:
        live = run(store,settings,maintenance,load_json(ROOT/daily['universe']),load_json(ROOT/daily['taxonomy']),
            None,None,db,ROOT/'committed-athena-index.sqlite3')
        propagate(store,settings,db)
    result['ongoing_content'] = live
    print(json.dumps(result),flush=True)
    return 0
