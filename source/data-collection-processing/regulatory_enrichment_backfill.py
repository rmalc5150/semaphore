"""Resume S22/S23 saved-record enrichment and email only after Athena verification."""
import argparse
import copy
import fcntl
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json, write_checked
from disclosure_collection import get_bytes
from regulatory_collection import CompanyMatcher, EvidenceClient, SourceIssue, require
from research_contract import ROOT, digest, load_json, seal_record

VERSION = "s22-s23-saved-enrichment-v1"
SOURCES = ("uk_mhra", "japan_pmda")


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
    data = copy.deepcopy(parent["payload"]["data"])
    if parent["source"] == "uk_mhra":
        data = {"category": data["category"], "record": data["record"]}
    else:
        # The original document text identifies a source version independently
        # of repeated retrieval dates and candidate entity matching.
        data = {key: data.get(key) for key in ("designationDate", "listNumber", "recordText")}
    return digest([parent["source"], parent["source_record_id"], data])


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
                require(parent["source"] == batch["source"] and parent["dataset"] == "research_records",
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
    payload = copy.deepcopy(parent["payload"])
    data = payload["data"]
    names = payload.get("company_names", [])
    extra_evidence = []
    outcome = "enriched"
    if parent["source"] == "uk_mhra":
        data["registerStatus"] = ("ilap_list" if data["category"] == "ilap" else
            "expired_or_removed_orphan_register" if "expired" in parent["source_url"].lower() else "current_orphan_register")
        if data["category"] == "orphan":
            import mhra_product_enrichment as mhra
            designation = data["record"].get("Designation number", "")
            def build():
                before = len(client.evidence)
                return mhra.enrich(client, designation), client.evidence[before:]
            result, extra_evidence = saved_lookup(db, "uk:" + digest(designation), build)
            data["holderEnrichment"] = {**result, "source_evidence": extra_evidence}
            names = list(dict.fromkeys(names + [r["name"] for r in result["companyRelationships"]]))
            if result["status"] != "verified_source_relationship":
                outcome = "gap"
        elif not names:
            outcome = "gap"
    else:
        import japan_pmda_designations as japan
        refs = [r for r in payload.get("source_evidence", []) if ".pdf" in r["source_url"].lower()]
        require(refs, "enrichment_original_pmda_pdf_missing")
        ref = refs[-1]
        def build():
            rows = japan.parse_pdf(get_bytes(client.store, ref["key"], ref["sha256"]))
            return {"sakigake:" + r["designationDate"] + ":" + r["listNumber"]: r for r in rows}, [ref]
        rows, extra_evidence = saved_lookup(db, "japan:" + ref["sha256"], build)
        require(parent["source_record_id"] in rows, "enrichment_pmda_identity_missing")
        data = copy.deepcopy(rows[parent["source_record_id"]])
        names = list(dict.fromkeys(r["name"] for r in data["companyRelationships"] if not r.get("nameReviewRequired")))
        payload["title"] = data["designatedProductName"]
        if data["applicantNameReviewRequired"]:
            outcome = "gap"
    payload.update(data=data, company_names=names)
    evidence = { (e["key"], e["sha256"]): e for e in payload.get("source_evidence", []) + extra_evidence }
    payload["source_evidence"] = list(evidence.values())
    return payload, outcome


def read_output(store, manifest_key):
    manifest = json.loads(get_bytes(store, manifest_key))
    batch = manifest["pages"][-1]["batches"][0]
    return json.loads(get_bytes(store, batch["key"], batch["sha256"]).splitlines()[0]), batch["key"]


def enrich_one(store, settings, config, universe, taxonomy, db, client, row):
    identity, source, parent_json, lineage_json, observations, attempts = row
    parent, lineage = json.loads(parent_json), json.loads(lineage_json)
    spec = task_spec(source, "research_records", "historical", config["window_start"], config["snapshot_cutoff"],
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
        except (SourceIssue, RuntimeError, ValueError) as exc:
            if attempts + 1 < config["max_attempts"]:
                raise
            payload, outcome = copy.deepcopy(parent["payload"]), "gap"
            payload["enrichment_error"] = exc.code if isinstance(exc, SourceIssue) else type(exc).__name__
        candidates, sectors = CompanyMatcher(universe).match(payload.get("company_names", []))
        payload.update(candidate_company_ids=candidates, candidate_sector_ids=sectors, company_match_basis="unverified_name")
        payload["regulatory_enrichment_backfill"] = {
            "job_id": config["job_id"], "version": VERSION, "source_version_id": identity,
            "prerequisite": lineage, "represented_observations": observations, "outcome": outcome,
            "original_ingested_at": parent["ingested_at"],
            "temporal_note": "Original event dates retained. UK holder evidence is from retrieved product information; historical ownership and current authorisation status are not inferred. Japan is re-parsed from its saved original PDF."}
        record = seal_record({**parent, "payload": payload, "run_id": run.run_id,
                              "ingested_at": now(), "universe_version": universe["universe_version"]})
        require(record["record_id"] == parent["record_id"] and record["event_at"] == parent["event_at"],
                "enrichment_identity_or_date_changed")
        run.commit_page([record], exhausted=True)
        manifest = run.finish("complete", expected_records=1)
        _, batch = read_output(store, manifest)
        return manifest, batch, record
    except (Exception, KeyboardInterrupt):
        run.finish("partial", "regulatory_enrichment_retry_required")
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
        "source IN ('uk_mhra','japan_pmda') AND dataset='research_records' AND "
        "json_extract_scalar(payload_json,'$.regulatory_enrichment_backfill.job_id')='" + config["job_id"] + "' GROUP BY source")
    actual = {row[0]: int(row[1]) for row in result["rows"]}
    require(actual == expected, "enrichment_athena_count_mismatch")
    subscriptions = [s for page in sns.get_paginator("list_subscriptions_by_topic").paginate(TopicArn=config["email_topic_arn"])
                     for s in page["Subscriptions"]]
    require(subscriptions and all(s["Protocol"] == "email" and s["Endpoint"] == config["email_recipient"] and
            s["SubscriptionArn"].startswith("arn:") for s in subscriptions), "enrichment_email_subscription_mismatch")
    gaps = [dict(zip(("source", "title", "outcome"), row)) for row in db.execute(
        "SELECT source,json_extract(parent,'$.payload.title'),outcome FROM versions WHERE outcome='gap'")]
    state.update(status="finished_with_gaps" if gaps else "complete", athena_verification=result,
                 verified_counts=actual, gaps=gaps, verified_at=now())
    message = sns.publish(TopicArn=config["email_topic_arn"],
        Subject="S22/S23 enrichment backfill complete" + (" - gaps recorded" if gaps else " - verified"),
        Message="The S22 UK MHRA and S23 Japan PMDA saved-record enrichment backfill has finished and is verified in "
        "optima_collected_data.observations.\n\n" + json.dumps(state, ensure_ascii=False, indent=2) +
        "\n\nReview the updated S22/S23 latest-version queries in ENTITY_DISCOVERY_ROLLOUT_PLAN.md#sql-checks. Original observations remain unchanged; "
        "use the latest enriched observation per provider ID. Company names are source relationships, not resolved internal company IDs. "
        "This enriches the pinned saved archive; it does not certify a reconstructed historical registry or historical company ownership.")
    state.update(notification_message_id=message["MessageId"], notified_at=now())
    return state


def execute(config):
    import boto3
    settings = StorageSettings.load(ROOT / config["storage_config"])
    store = settings.store()
    state_key = "operations/regulatory/enrichment-backfill/" + config["job_id"] + "/state.json"
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
        clients = {source: EvidenceClient(store, source) for source in SOURCES}
        if not remaining:
            rows = db.execute("SELECT id,source,parent,lineage,observations,attempts FROM versions "
                "WHERE status!='done' AND retry_after<=? ORDER BY source,id LIMIT ?",
                (now(), config["max_versions_per_invocation"])).fetchall()
            for row in rows:
                try:
                    manifest, batch, record = enrich_one(store, settings, config, universe, taxonomy, db, clients[row[1]], row)
                except (SourceIssue, RuntimeError, ValueError) as exc:
                    retry = (datetime.now(timezone.utc) + timedelta(minutes=config["retry_minutes"])).isoformat().replace("+00:00", "Z")
                    with db:
                        db.execute("UPDATE versions SET attempts=attempts+1,retry_after=?,status='retry' WHERE id=?", (retry, row[0]))
                    print(json.dumps({"stage": "retry", "source": row[1], "error": type(exc).__name__}), flush=True)
                    continue
                with db:
                    db.execute("UPDATE versions SET status='done',attempts=attempts+1,manifest=?,batch_key=?,output_id=?,outcome=? WHERE id=?",
                        (manifest, batch, record["observation_id"], record["payload"]["regulatory_enrichment_backfill"]["outcome"], row[0]))
                print(json.dumps({"stage": "enriched", "source": row[1], "source_record_id": record["source_record_id"],
                                  "outcome": record["payload"]["regulatory_enrichment_backfill"]["outcome"]}), flush=True)
        state = {"job_id": config["job_id"], "status": "running", "updated_at": now(), "remaining_batches": remaining,
            "pending_versions": db.execute("SELECT count(*) FROM versions WHERE status!='done'").fetchone()[0],
            "counts": [dict(zip(("source", "status", "outcome", "versions", "represented_observations"), row)) for row in
                       db.execute("SELECT source,status,outcome,count(*),sum(observations) FROM versions GROUP BY source,status,outcome")],
            "scope_note": config["scope_note"]}
        state = notify_when_verified(store, db, config, boto3.client("sns", region_name=settings.region), state,
            ROOT / "committed-athena-index.sqlite3", boto3.client("athena", region_name=settings.region))
        existing = store.get(state_key)
        write_json(store, state_key, state, existing.token if existing else None)
        report = ROOT / "reports" / (config["job_id"] + "-latest.json")
        report.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/regulatory-enrichment-backfill.json")
    args = parser.parse_args()
    with (ROOT / ".regulatory-enrichment-backfill.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 2
        result = execute(load_json(ROOT / args.config))
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
