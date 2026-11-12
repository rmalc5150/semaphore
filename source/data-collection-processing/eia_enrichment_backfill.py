"""Enrich the pinned S56 EIA index and retail archive and email after Athena verification."""
import argparse
import copy
import fcntl
import hashlib
import json
import sqlite3
from xml.etree.ElementTree import ParseError
from datetime import datetime, timedelta, timezone
from pathlib import Path

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json, write_checked
from disclosure_collection import get_bytes
from regulatory_collection import EvidenceClient, SourceIssue, require
from research_contract import ROOT, digest, load_json, seal_record

VERSION = "s56-index-retail-v1"
SOURCES = ("eia_generator_index", "eia_retail_prices")


def registry(path):
    db = sqlite3.connect(path)
    db.executescript('''
      CREATE TABLE IF NOT EXISTS batches (key TEXT PRIMARY KEY);
      CREATE TABLE IF NOT EXISTS versions (
        id TEXT PRIMARY KEY, source TEXT, parent TEXT, lineage TEXT,
        observations INTEGER DEFAULT 1, status TEXT DEFAULT 'pending',
        attempts INTEGER DEFAULT 0, retry_after TEXT DEFAULT '',
        manifest TEXT, batch_key TEXT, output_id TEXT, outcome TEXT);
      CREATE TABLE IF NOT EXISTS lookups (id TEXT PRIMARY KEY, result TEXT, evidence TEXT);
    ''')
    return db


def version_identity(parent):
    data = parent['payload']['data']
    return digest([parent['source'], parent['source_record_id'], {k:v for k,v in data.items() if k != 'enrichment'}])


def discover(store, db, config, inventory):
    processed = 0
    for batch in inventory["batches"]:
        if db.execute("SELECT 1 FROM batches WHERE key=?", (batch["key"],)).fetchone():
            continue
        if processed >= config["max_batches_per_invocation"]:
            break
        raw = get_bytes(store, batch["key"], batch["sha256"])
        rows = [json.loads(line) for line in raw.splitlines()]
        require(len(rows) == batch["records"], "enrichment_input_batch_count_mismatch")
        with db:
            for parent in rows:
                require(parent["source"] == batch["source"] and parent["dataset"] == "specialist_inputs",
                        "enrichment_input_scope_mismatch")
                if parent["ingested_at"] >= config["snapshot_cutoff"]:
                    continue
                identity = version_identity(parent)
                lineage = {"batch_key": batch["key"], "batch_sha256": batch["sha256"],
                           "observation_id": parent["observation_id"], "record_id": parent["record_id"]}
                old = db.execute("SELECT parent FROM versions WHERE id=?", (identity,)).fetchone()
                if old is None:
                    db.execute("INSERT INTO versions(id,source,parent,lineage) VALUES (?,?,?,?)",
                               (identity, parent["source"], json.dumps(parent), json.dumps(lineage)))
                else:
                    db.execute("UPDATE versions SET observations=observations+1 WHERE id=?", (identity,))
                    if parent["ingested_at"] > json.loads(old[0])["ingested_at"]:
                        db.execute("UPDATE versions SET parent=?,lineage=? WHERE id=?",
                                   (json.dumps(parent), json.dumps(lineage), identity))
            db.execute("INSERT INTO batches VALUES (?)", (batch["key"],))
        processed += 1
        if processed % 25 == 0:
            print(json.dumps({"stage": "inventory", "batches_processed": processed}), flush=True)
    return len(inventory["batches"]) - db.execute("SELECT count(*) FROM batches").fetchone()[0]


def saved_lookup(db, key, build):
    old = db.execute("SELECT result,evidence FROM lookups WHERE id=?", (key,)).fetchone()
    if old:
        return json.loads(old[0]), json.loads(old[1])
    result, evidence = build()
    with db:
        db.execute("INSERT INTO lookups VALUES (?,?,?)", (key, json.dumps(result), json.dumps(evidence)))
    return result, evidence


def source_enrichment(parent, client, db):
    from eia_enrichment import enrich_archive,retail_metadata,retail_history,retail_row,month_shift,number,published_links
    payload=copy.deepcopy(parent['payload']);source=parent['source']
    def build():
        start=len(client.evidence)
        if source=='eia_generator_index':
            index_evidence=next((e for e in payload.get('source_evidence',[]) if e.get('source_url','').rstrip('/')=='https://www.eia.gov/electricity/data/eia860m'),None)
            if index_evidence:
                html=get_bytes(client.store,index_evidence['key'],index_evidence['sha256'])
                links=published_links(html,index_evidence['source_url'])
                if payload['data']['archive_url'] not in links:
                    return {'version':'eia-index-retail-v1','status':'not_applicable_unpublished_template_link',
                        'workbook_validated':False,'event_candidate':None,
                        'note':'Old regex discovered a link inside non-anchor/commented index content; no published workbook is established.'},[]
            value=enrich_archive(payload['data']['archive_url'],client)
        else:
            period=payload['data']['period']
            meta=retail_metadata(client)
            history=retail_history(client,month_shift(period,-12),period)
            row=next((r for r in history if r['period']==period),None)
            require(row is not None,'eia_backfill_target_month_missing')
            value=retail_row(row,history,meta)
        return value,copy.deepcopy(client.evidence[start:])
    lookup=('index:'+payload['data']['archive_url']) if source=='eia_generator_index' else 'retail:'+payload['data']['period']
    value,evidence=saved_lookup(db,lookup,build)
    if source=='eia_generator_index':
        payload['data']['enrichment']=value
        payload['record_type']='generator_archive_provenance'
    else:
        payload['data']['enrichment']=copy.deepcopy(value['enrichment'])
        current={k:v for k,v in value.items() if k!='enrichment'}
        payload['data']['enrichment']['current_retrieved_row']=current
        payload['data']['enrichment']['original_observation_comparison']={
            'original_ingested_at':parent['ingested_at'],
            'changed_original_fields':[k for k in ['price','price-units','sales','revenue','customers']
                if k in payload['data'] and ((number(payload['data'].get(k))!=number(current.get(k))) if k!='price-units' and number(payload['data'].get(k)) is not None and number(current.get(k)) is not None else payload['data'].get(k)!=current.get(k))],
            'note':'Original saved row preserved. Added fields and baselines are a current API retrieval, not a recovered original vintage.'}
        payload['record_type']='retail_electricity_series_observation'
    payload['source_evidence']=payload.get('source_evidence',[])+evidence
    payload['coverage_note']='S56 enriched index provenance or US all-sector retail context; battery collection unchanged; historical availability unverified.'
    return payload,payload['data']['enrichment']['status']


def read_output(store, manifest_key):
    manifest = json.loads(get_bytes(store, manifest_key))
    batch = manifest["pages"][-1]["batches"][0]
    return json.loads(get_bytes(store, batch["key"], batch["sha256"]).splitlines()[0]), batch["key"]


def enrich_one(store, settings, config, universe, taxonomy, db, client, row):
    identity, source, parent_json, lineage_json, observations, attempts = row
    parent, lineage = json.loads(parent_json), json.loads(lineage_json)
    spec = task_spec(source, "specialist_inputs", "historical", config["window_start"], config["snapshot_cutoff"],
        {"enrichment_job_id": config["job_id"], "source_version_id": identity, "inventory_sha256": config["inventory_sha256"]},
        VERSION, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
    except AlreadyComplete as exc:
        record, batch = read_output(store, str(exc))
        return str(exc), batch, record
    if run.exhausted:
        manifest = run.finish("complete", expected_records=1)
        record, batch = read_output(store, manifest)
        return manifest, batch, record
    try:
        try:
            payload, outcome = source_enrichment(parent, client, db)
        except (SourceIssue, RuntimeError, ValueError, KeyError, ParseError) as exc:
            if isinstance(exc,SourceIssue) and (exc.code.startswith('source_http_5') or exc.code in {'authenticated_source_request_failed','credential_unavailable','source_http_429','eia_empty_workbook_response'}):
                raise
            if attempts + 1 < config["max_attempts"]:
                raise
            payload, outcome = copy.deepcopy(parent["payload"]), "gap"
            payload["enrichment_error"] = exc.code if isinstance(exc, SourceIssue) else type(exc).__name__
        payload["eia_enrichment_backfill"] = {
            "job_id": config["job_id"], "version": VERSION, "source_version_id": identity,
            "prerequisite": lineage, "represented_observations": observations, "outcome": outcome,
            "original_ingested_at": parent["ingested_at"],
            "temporal_note": "Original observation identity, data and event_at retained. Workbook month, retail reference month, current retrieval and release dates remain separate. Battery observations are not reprocessed. Added workbook/API fields are not reconstructed historical publication vintages."}
        record = seal_record({**parent, "payload": payload, "run_id": run.run_id,
                              "ingested_at": now(), "universe_version": universe["universe_version"]})
        require(record["record_id"] == parent["record_id"] and record["event_at"] == parent["event_at"],
                "enrichment_identity_or_date_changed")
        run.commit_page([record], exhausted=True)
        manifest = run.finish("complete", expected_records=1)
        _, batch = read_output(store, manifest)
        return manifest, batch, record
    except (Exception, KeyboardInterrupt):
        run.finish("partial", "eia_enrichment_retry_required")
        raise


def publication_ready(db, index_path):
    required = [r[0] for r in db.execute("SELECT batch_key FROM versions WHERE status='done'")]
    if not required:
        return False
    with sqlite3.connect("file:" + str(index_path) + "?mode=ro", uri=True) as index:
        return all(index.execute("SELECT 1 FROM verified_batches WHERE key=?", (key,)).fetchone() for key in required)


def notify_when_verified(store, db, config, sns, state, index_path, athena):
    if state.get("notification_message_id") or state["remaining_batches"] or state["pending_versions"]:
        return state
    if not publication_ready(db, index_path):
        state["status"] = "awaiting_athena_publication"
        return state
    from committed_data_athena import query
    expected = dict(db.execute("SELECT source,count(*) FROM versions WHERE status='done' GROUP BY source").fetchall())
    result = query(athena, "SELECT source,count(*) FROM optima_collected_data.observations WHERE "
        "source IN ('eia_generator_index','eia_retail_prices') AND dataset='specialist_inputs' AND "
        "json_extract_scalar(payload_json,'$.eia_enrichment_backfill.job_id')='" + config["job_id"] + "' GROUP BY source")
    actual = {row[0]: int(row[1]) for row in result["rows"]}
    require(actual == expected, "enrichment_athena_count_mismatch")
    subscriptions = [s for page in sns.get_paginator("list_subscriptions_by_topic").paginate(TopicArn=config["email_topic_arn"])
                     for s in page["Subscriptions"]]
    require(subscriptions and all(s["Protocol"] == "email" and s["Endpoint"] == config["email_recipient"] and
            s["SubscriptionArn"].startswith("arn:") for s in subscriptions), "enrichment_email_subscription_mismatch")
    gaps = [dict(zip(("source", "source_record_id", "outcome"), row)) for row in db.execute(
        "SELECT source,json_extract(parent,'$.source_record_id'),outcome FROM versions WHERE outcome IN ('gap','review_required')")]
    gap_key = "operations/eia-enrichment/enrichment-backfill/" + config["job_id"] + "/gaps.json"
    write_json(store, gap_key, gaps)
    state.update(status="finished_with_gaps" if gaps else "complete", athena_verification=result,
                 verified_counts=actual, gap_count=len(gaps), gaps=gaps[:20],
                 gap_receipt=gap_key, verified_at=now())
    message = sns.publish(TopicArn=config["email_topic_arn"],
        Subject="S56 EIA index and retail enrichment backfill complete" + (" - gaps recorded" if gaps else " - verified"),
        Message="The S56 EIA index and retail saved-record enrichment backfill has finished and is verified in "
        "optima_collected_data.observations.\n\n" + json.dumps(state, ensure_ascii=False, indent=2) +
        "\n\nOnly eia_generator_index and eia_retail_prices were enriched; battery collection was unchanged. "
        "Index workbooks and battery rows are one provenance chain; prices are US all-sector retail averages. "
        "Original observations and current-retrieved context remain separate. See S56_EIA_ENRICHMENT.md "
        "and the pending integration notes in ENTITY_DISCOVERY_ROLLOUT_PLAN.md#event-pipeline for scope and limitations.")
    state.update(notification_message_id=message["MessageId"], notified_at=now())
    return state


def execute(config):
    import boto3
    settings = StorageSettings.load(ROOT / config["storage_config"])
    store = settings.store()
    state_key = "operations/eia-enrichment/enrichment-backfill/" + config["job_id"] + "/state.json"
    prior = store.get(state_key)
    if prior and json.loads(prior.body).get("notification_message_id"):
        return json.loads(prior.body)
    raw = (ROOT / config["inventory_file"]).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == config["inventory_sha256"], "enrichment_inventory_changed")
    prefix = state_key.rsplit("/", 1)[0]
    write_checked(store, prefix + "/input-batches.json", raw, content_type="application/json")
    write_checked(store, prefix + "/config.json", (json.dumps(config, sort_keys=True) + "\n").encode(), content_type="application/json")
    if not prior:
        write_json(store, state_key, {"job_id": config["job_id"], "status": "discovering_saved_versions",
            "started_at": now(), "input_batches": len(json.loads(raw)["batches"]), "scope_note": config["scope_note"]})
    universe, taxonomy = load_json(ROOT / config["universe"]), load_json(ROOT / config["taxonomy"])
    with registry(ROOT / (config["job_id"] + ".sqlite3")) as db:
        remaining = discover(store, db, config, json.loads(raw))
        coverage_raw=(ROOT/config['retail_coverage_file']).read_bytes()
        require(hashlib.sha256(coverage_raw).hexdigest()==config['retail_coverage_sha256'],'eia_coverage_receipt_changed')
        coverage=json.loads(coverage_raw)
        if not remaining:
            present={r[0] for r in db.execute("SELECT DISTINCT json_extract(parent,'$.payload.data.period') FROM versions WHERE source='eia_retail_prices'")}
            require(set(coverage['required_periods'])<=present,'eia_backfill_original_month_gap')
        write_checked(store,prefix+'/retail-coverage.json',coverage_raw,content_type='application/json')
        clients = {source: EvidenceClient(store, source) for source in SOURCES}
        defer_file=ROOT/('reports/'+config['job_id']+'-retail-retry.json')
        deferred=json.loads(defer_file.read_text()) if defer_file.exists() else {}
        if not remaining:
            rows = db.execute("SELECT id,source,parent,lineage,observations,attempts FROM versions "
                "WHERE status!='done' AND retry_after<=? ORDER BY source,id LIMIT ?",
                (now(), config["max_versions_per_invocation"])).fetchall()
            for row in rows:
                if row[1]=='eia_retail_prices' and deferred.get('retry_after','')>now():continue
                try:
                    manifest, batch, record = enrich_one(store, settings, config, universe, taxonomy, db, clients[row[1]], row)
                except (SourceIssue, RuntimeError, ValueError, KeyError, ParseError) as exc:
                    if isinstance(exc,SourceIssue) and (exc.code.startswith('source_http_5') or exc.code in {'authenticated_source_request_failed','credential_unavailable','source_http_429','eia_empty_workbook_response'}):
                        deferred={'retry_after':(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat().replace('+00:00','Z'),'reason':exc.code}
                        if row[1]=='eia_retail_prices':defer_file.write_text(json.dumps(deferred))
                        print(json.dumps({'stage':'provider_deferred','source':row[1],'reason':exc.code}),flush=True)
                        break
                    retry = (datetime.now(timezone.utc) + timedelta(minutes=config["retry_minutes"])).isoformat().replace("+00:00", "Z")
                    with db:
                        db.execute("UPDATE versions SET attempts=attempts+1,retry_after=?,status='retry' WHERE id=?", (retry, row[0]))
                    print(json.dumps({"stage": "retry", "source": row[1], "error": type(exc).__name__}), flush=True)
                    continue
                with db:
                    db.execute("UPDATE versions SET status='done',attempts=attempts+1,manifest=?,batch_key=?,output_id=?,outcome=? WHERE id=?",
                        (manifest, batch, record["observation_id"], record["payload"]["eia_enrichment_backfill"]["outcome"], row[0]))
                print(json.dumps({"stage": "enriched", "source": row[1], "source_record_id": record["source_record_id"],
                                  "outcome": record["payload"]["eia_enrichment_backfill"]["outcome"]}), flush=True)
        state = {"job_id": config["job_id"], "status": "running", "updated_at": now(), "remaining_batches": remaining,
            "pending_versions": db.execute("SELECT count(*) FROM versions WHERE status!='done'").fetchone()[0],
            "counts": [dict(zip(("source", "status", "outcome", "versions", "represented_observations"), row)) for row in
                       db.execute("SELECT source,status,outcome,count(*),sum(observations) FROM versions GROUP BY source,status,outcome")],
            "scope_note": config["scope_note"]}
        state['retail_provider_retry']=deferred
        if deferred.get('retry_after','')>now():state['status']='retail_provider_deferred'
        state = notify_when_verified(store, db, config, boto3.client("sns", region_name=settings.region), state,
            ROOT / "committed-athena-index.sqlite3", boto3.client("athena", region_name=settings.region))
        existing = store.get(state_key)
        write_json(store, state_key, state, existing.token if existing else None)
        report = ROOT / "reports" / (config["job_id"] + "-latest.json")
        report.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/eia-enrichment-backfill.json")
    args = parser.parse_args()
    with (ROOT / ".eia-enrichment-backfill.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 2
        result = execute(load_json(ROOT / args.config))
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
