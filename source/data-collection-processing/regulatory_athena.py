#!/usr/bin/env python3
"""Curate committed clinical/regulatory records into an immutable Athena pilot."""
from collections import defaultdict
from datetime import date
import argparse
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from collection_storage import StorageSettings
from research_contract import ROOT, canonical_json, digest, load_json, validate_record, validate_universe
from regulatory_sources import ADAPTERS
import sec_athena_pilot as release

VERSION = "regulatory-curation-1.0"
COMMON = [("record_id", "string"), ("version_id", "string"), ("source", "string"),
    ("provider_id", "string"), ("record_type", "string"), ("title", "string"),
    ("event_date", "date"), ("date_basis", "string"), ("source_updated_date", "date"),
    ("available_at", "string"), ("availability_basis", "string"), ("source_url", "string"),
    ("data_json", "string"), ("company_names", "array<string>"),
    ("first_observed_at", "string"), ("last_observed_at", "string"), ("observation_count", "bigint"),
    ("coverage_note", "string")]
SCHEMAS = {"research_records": COMMON + [("version_count", "bigint")], "record_versions": COMMON,
    "record_observations": [("observation_id", "string"), ("record_id", "string"), ("version_id", "string"),
        ("run_id", "string"), ("ingested_at", "string"), ("manifest_keys", "array<string>"),
        ("raw_batch_keys", "array<string>"), ("evidence_keys", "array<string>"), ("record_json", "string")],
    "record_companies": [("record_id", "string"), ("company_id", "string"), ("match_status", "string")],
    **{name: release.SCHEMAS[name] for name in ("companies", "company_sectors")}}
for name in ("clinical_trials", "regulatory_events", "regulatory_snapshots"):
    SCHEMAS[name] = SCHEMAS["research_records"]


def read_inputs(store, keys, allowed=None, dataset="research_records", consume=None):
    if consume is not None:
        release.require(len(set(keys)) == 1, "Streaming curation requires one manifest per window")
    entries, inputs, universe_hash, verified_evidence = {}, [], None, set()
    allowed = {adapter.source for adapter in ADAPTERS.values()} if allowed is None else set(allowed)
    for key in sorted(set(keys)):
        raw = release.get_bytes(store, key)
        manifest = json.loads(raw)
        task = manifest["task"]
        release.require(manifest["status"] == "complete" and manifest["exhausted"], "Only complete runs can be curated")
        release.require(task["source"] in allowed and task["dataset"] == dataset, "Unsupported source")
        task_id = "task_" + digest(task)
        head = json.loads(release.get_bytes(store, f"checkpoints/{task_id}/head.json"))
        release.require(manifest["task_id"] == task_id and head["task"] == task and key in head["terminal_history"], "Uncommitted manifest")
        universe = json.loads(release.get_bytes(store, f"manifests/configurations/universe/{task['universe_hash']}.json"))
        taxonomy = json.loads(release.get_bytes(store, f"manifests/configurations/taxonomy/{task['taxonomy_hash']}.json"))
        release.require(digest(universe) == task["universe_hash"] and digest(taxonomy) == task["taxonomy_hash"], "Configuration checksum mismatch")
        release.require(not validate_universe(universe, taxonomy)[0], "Invalid configuration")
        release.require(universe_hash is None or universe_hash == task["universe_hash"], "Resolve mixed universe snapshots before curation")
        universe_hash = task["universe_hash"]
        count, seen = 0, set()
        for page in manifest["pages"]:
            page_count = 0
            for batch in page["batches"]:
                body = release.get_bytes(store, batch["key"])
                release.require(hashlib.sha256(body).hexdigest() == batch["sha256"] and len(body) == batch["bytes"], "Raw checksum mismatch")
                rows = [json.loads(line) for line in body.splitlines()]
                release.require(len(rows) == batch["records"], "Raw count mismatch")
                for record in rows:
                    release.require(not validate_record(record, universe), "Invalid record")
                    release.require(record["source"] == task["source"] and record["dataset"] == task["dataset"] and
                        record["run_id"] == page["run_id"] and record["universe_version"] == universe["universe_version"], "Record scope mismatch")
                    identity = record["observation_id"]
                    release.require(identity not in seen, "Duplicate observation in manifest")
                    seen.add(identity)
                    evidence = record["payload"]["source_evidence"]
                    release.require(evidence, "Missing source evidence")
                    for ref in evidence:
                        pair = (ref["key"], ref["sha256"])
                        if pair not in verified_evidence:
                            release.require(hashlib.sha256(release.get_bytes(store, ref["key"])).hexdigest() == ref["sha256"], "Source evidence checksum mismatch")
                            verified_evidence.add(pair)
                    if consume is not None:
                        consume({"record": record, "manifests": {key}, "batches": {batch['key']}})
                        continue
                    entry = entries.setdefault(identity, {"record": record, "manifests": set(), "batches": set()})
                    release.require(entry["record"] == record, "Conflicting observation")
                    entry["manifests"].add(key)
                    entry["batches"].add(batch["key"])
                page_count += len(rows)
            release.require(page_count == page["record_count"], "Page count mismatch")
            count += page_count
        release.require(count == manifest["record_count"] == manifest["expected_records"], "Manifest count mismatch")
        inputs.append({"key": key, "sha256": hashlib.sha256(raw).hexdigest(), "records": count})
    release.require(universe_hash is not None, "Select completed source manifests")
    return entries, universe, inputs


def semantic_id(record):
    semantic = {k: v for k, v in record.items() if k not in {"run_id", "ingested_at", "observation_id", "payload_hash"}}
    semantic["payload"] = {k: v for k, v in record["payload"].items() if k != "source_evidence"}
    return "ver_" + digest(semantic)


def curate(entries, universe):
    tables = {name: [] for name in SCHEMAS}
    dimensions = release.curate({}, universe)
    for name in ("companies", "company_sectors"):
        tables[name] = dimensions[name]
    groups = defaultdict(list)
    for identity, entry in sorted(entries.items()):
        record = entry["record"]
        groups[record["record_id"]].append(record)
        tables["record_observations"].append({"observation_id": identity, "record_id": record["record_id"],
            "version_id": semantic_id(record), "run_id": record["run_id"], "ingested_at": record["ingested_at"],
            "manifest_keys": sorted(entry["manifests"]), "raw_batch_keys": sorted(entry["batches"]),
            "evidence_keys": sorted({x["key"] for x in record["payload"]["source_evidence"]}),
            "record_json": release.json_text(record)})
    for record_id, members in sorted(groups.items()):
        latest = max(members, key=release.observed_order)
        versions = defaultdict(list)
        for record in members:
            versions[semantic_id(record)].append(record)
        for version, records in sorted(versions.items()):
            record = max(records, key=release.observed_order)
            payload = record["payload"]
            row = {"record_id": record_id, "version_id": version, "source": record["source"],
                "provider_id": record["source_record_id"], "record_type": payload["record_type"], "title": payload.get("title"),
                "event_date": date.fromisoformat(record["event_at"]["value"]) if record["event_at"] else None,
                "date_basis": payload["date_basis"],
                "source_updated_date": date.fromisoformat(record["source_updated_at"]["value"]) if record["source_updated_at"] else None,
                "available_at": record["available_at"]["value"] if record["available_at"] else None,
                "availability_basis": record["availability_basis"], "source_url": record["source_url"],
                "data_json": release.json_text(payload["data"]), "company_names": payload["company_names"],
                "first_observed_at": min(records, key=release.observed_order)["ingested_at"],
                "last_observed_at": record["ingested_at"], "observation_count": len(records),
                "coverage_note": payload["coverage_note"]}
            tables["record_versions"].append(row)
            if version == semantic_id(latest):
                current = {**row, "version_count": len(versions), "observation_count": len(members),
                           "first_observed_at": min(members, key=release.observed_order)["ingested_at"]}
                tables["research_records"].append(current)
                type_table = {"clinical_trial": "clinical_trials", "regulatory_event": "regulatory_events",
                              "regulatory_snapshot": "regulatory_snapshots"}[payload["record_type"]]
                tables[type_table].append(current)
        for cid in sorted(set(latest["payload"]["candidate_company_ids"])):
            tables["record_companies"].append({"record_id": record_id, "company_id": cid, "match_status": "candidate"})
    return tables


def prepare(store, settings, config, output_root):
    release.validate_config(config)
    entries, universe, inputs = read_inputs(store, config["source_manifests"])
    tables = curate(entries, universe)
    release_id = digest({"version": VERSION, "arrow": pa.__version__, "inputs": inputs,
        "schemas": SCHEMAS, "config": config, "bucket": settings.s3_bucket, "prefix": settings.s3_prefix})
    root = Path(output_root) / release_id
    root.mkdir(parents=True, exist_ok=True)
    prefix = config["curated_prefix"] + "/" + release_id
    files, ddl = {}, []
    for name, rows in tables.items():
        table = pa.Table.from_pylist(rows, schema=pa.schema([(field, release.ARROW_TYPES[kind]) for field, kind in SCHEMAS[name]]))
        relative = f"tables/{name}/part-00000.parquet"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, path, compression="snappy", version="1.0")
        release.require(pq.ParquetFile(path).read().equals(table), "Parquet round-trip mismatch")
        body = path.read_bytes()
        location = f"s3://{settings.s3_bucket}/{settings.s3_prefix}/{prefix}/tables/{name}/"
        files[name] = {"path": relative, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                       "rows": len(rows), "location": location, "columns": SCHEMAS[name]}
        columns = ", ".join(f"{field} {kind}" for field, kind in SCHEMAS[name])
        ddl.append(f"CREATE EXTERNAL TABLE {config['database']}.{name} ({columns}) STORED AS PARQUET LOCATION '{location}';")
    db = config["database"]
    queries = {
        "table_counts": " UNION ALL ".join(f"SELECT '{name}' AS table_name, count(*) AS records FROM {db}.{name}" for name in SCHEMAS) + " ORDER BY table_name",
        "source_counts": f"SELECT source, record_type, count(*) AS records FROM {db}.research_records GROUP BY source, record_type ORDER BY source, record_type",
        "quality": f"SELECT count(*), count(DISTINCT record_id), sum(observation_count), count(available_at) FROM {db}.research_records",
        "preview": f"SELECT source, provider_id, record_type, event_date, date_basis, title FROM {db}.research_records ORDER BY source, provider_id LIMIT 20"}
    counts = defaultdict(int)
    for record in tables["research_records"]:
        counts[record["source"], record["record_type"]] += 1
    expected = {"table_counts": [[name, str(len(rows))] for name, rows in sorted(tables.items())],
        "source_counts": [[source, kind, str(count)] for (source, kind), count in sorted(counts.items())],
        "quality": [[str(len(tables["research_records"])), str(len(tables["research_records"])),
                     str(len(tables["record_observations"])) if tables["research_records"] else None,
                     str(sum(r["available_at"] is not None for r in tables["research_records"]))]]}
    report = {"curator_version": VERSION, "catalog_owner": "regulatory", "workgroup_description": "Optima regulatory pilot",
        "release_id": release_id, "release_prefix": prefix, "bucket": settings.s3_bucket, "s3_prefix": settings.s3_prefix,
        "config": config, "inputs": inputs, "universe_hash": digest(universe), "files": files,
        "expected_results": expected, "queries": queries, "status": "locally_validated", "schema_version": "1.0"}
    (root / "release.json").write_bytes(canonical_json(report) + b"\n")
    (root / "tables.sql").write_text("\n\n".join(ddl) + "\n")
    (root / "queries.sql").write_text("\n\n".join(f"-- {name}\n{query};" for name, query in queries.items()) + "\n")
    print(json.dumps({"stage": "prepared", "directory": str(root), "expected_results": expected}), flush=True)
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "publish", "deploy"))
    parser.add_argument("--config", type=Path, default=ROOT / "config/regulatory-athena-pilot.json")
    parser.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "regulatory-athena-build")
    parser.add_argument("--release-dir", type=Path)
    parser.add_argument("--update-existing", action="store_true",
                        help="advance owned Glue tables to this immutable release")
    args = parser.parse_args()
    settings = StorageSettings.load(args.storage_config)
    store = settings.store()
    if args.stage == "prepare":
        prepare(store, settings, load_json(args.config), args.output_root)
    else:
        release.require(args.release_dir is not None, "--release-dir is required")
        if args.stage == "publish":
            release.publish(store, settings, args.release_dir)
        else:
            release.deploy(store, settings, args.release_dir, args.update_existing)


if __name__ == "__main__":
    main()
