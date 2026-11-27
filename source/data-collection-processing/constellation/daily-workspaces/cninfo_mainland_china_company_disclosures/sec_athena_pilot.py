#!/usr/bin/env python3
"""Build an immutable, bounded SEC research release and register it in Athena.

prepare reads explicitly selected committed manifests and writes local Parquet.
publish verifies and uploads that exact release. deploy creates pilot-only Glue
tables/workgroup and checks SQL results. No IAM changes or scheduled jobs.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import time

import pyarrow as pa
import pyarrow.parquet as pq

from collection_storage import StorageSettings, checked_key, write_checked
from research_contract import ROOT, canonical_json, digest, load_json, parse_instant, validate_record, validate_universe
from sec_filings import parse_index

VERSION = "sec-curation-1.1"
COMMON = [
    ("record_id", "string"), ("version_id", "string"), ("accession_number", "string"),
    ("form", "string"), ("filing_date", "date"), ("source_url", "string"),
    ("issuer_ciks", "array<string>"), ("issuer_rows_json", "string"),
    ("document_urls", "array<string>"), ("entity_match_status", "string"),
    ("available_at", "string"), ("availability_precision", "string"),
    ("availability_basis", "string"), ("universe_version", "string"),
    ("payload_hash", "string"), ("payload_json", "string"),
    ("first_observed_at", "string"), ("last_observed_at", "string"),
    ("observation_count", "bigint")]
SCHEMAS = {
    "sec_filings": COMMON + [("version_count", "bigint")],
    "sec_filing_versions": COMMON,
    "sec_observations": [
        ("observation_id", "string"), ("record_id", "string"), ("version_id", "string"),
        ("run_id", "string"), ("ingested_at", "string"), ("payload_hash", "string"),
        ("source_manifest_keys", "array<string>"), ("raw_batch_keys", "array<string>"),
        ("source_snapshot_keys", "array<string>"), ("record_json", "string")],
    "sec_filing_companies": [
        ("record_id", "string"), ("version_id", "string"), ("company_id", "string"),
        ("match_status", "string"), ("match_basis", "string")],
    "companies": [
        ("company_id", "string"), ("canonical_name", "string"), ("entity_type", "string"),
        ("review_status", "string"), ("collection_enabled", "boolean"),
        ("universe_version", "string"), ("observed_at", "string"), ("company_json", "string")],
    "company_sectors": [
        ("company_id", "string"), ("sector_id", "string"), ("subsector_ids", "array<string>"),
        ("review_status", "string"), ("classification_basis", "string"),
        ("valid_from", "date"), ("valid_to", "date"), ("observed_at", "string"),
        ("evidence_json", "string")]
}
ARROW_TYPES = {"string": pa.string(), "date": pa.date32(), "bigint": pa.int64(),
               "boolean": pa.bool_(), "array<string>": pa.list_(pa.string())}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def json_text(value):
    return canonical_json(value).decode()


def get_bytes(store, key):
    obj = store.get(key)
    require(obj is not None, f"Missing required object: {key}")
    return obj.body


def evidence_identity(item):
    return hashlib.sha256(canonical_json(item)).digest()


def read_inputs(store, manifest_keys):
    """Only committed complete manifests are eligible, including historical ones.

    Never scan raw prefixes: they may contain orphan writes or partial attempts.
    A bounded in-memory pilot, not an unbounded historical processing engine.
    """
    require(bool(manifest_keys), "Select at least one manifest")
    entries, inputs, universes, snapshots = {}, [], {}, {}
    for key in sorted(set(manifest_keys)):
        body = get_bytes(store, key)
        manifest = json.loads(body)
        task = manifest["task"]
        require(task["source"] == "sec_edgar" and task["dataset"] == "filings", "Not an SEC filing run")
        require(manifest["status"] == "complete" and manifest["exhausted"], "Run is not complete and exhausted")
        task_id = "task_" + digest(task)
        require(manifest["task_id"] == task_id, "Task hash mismatch")
        head = json.loads(get_bytes(store, f"checkpoints/{task_id}/head.json"))
        require(head["task"] == task and key in head["terminal_history"], "Manifest is not committed")
        universe_hash = task["universe_hash"]
        universe = json.loads(get_bytes(store, f"manifests/configurations/universe/{universe_hash}.json"))
        taxonomy = json.loads(get_bytes(store, f"manifests/configurations/taxonomy/{task['taxonomy_hash']}.json"))
        require(digest(universe) == universe_hash and digest(taxonomy) == task["taxonomy_hash"], "Configuration hash mismatch")
        require(not validate_universe(universe, taxonomy)[0], "Invalid universe/taxonomy")
        universes[universe_hash] = universe
        require(len(universes) == 1, "Pilot requires one universe snapshot; resolve schema/identity changes explicitly")
        snapshot = json.loads(get_bytes(store, key.rsplit("/", 1)[0] + "/input.json"))
        if snapshot["key"] not in snapshots:
            source = get_bytes(store, snapshot["key"])
            require(hashlib.sha256(source).hexdigest() == snapshot["sha256"], "Source snapshot hash mismatch")
            evidence = set()
            parse_index(source, snapshot["year"], snapshot["quarter"], consume=lambda row:
                evidence.add(evidence_identity(tuple(row[k] for k in (
                    "accession_number", "cik", "company_name", "form", "filing_date", "filename")))))
            del source
            snapshots[snapshot["key"]] = (snapshot["sha256"], evidence)
        source_hash, evidence = snapshots[snapshot["key"]]
        require(source_hash == snapshot["sha256"], "Conflicting source snapshot metadata")
        count, run_ids = 0, set()
        for page in manifest["pages"]:
            page_count = 0
            for batch in page["batches"]:
                raw = get_bytes(store, batch["key"])
                require(len(raw) == batch["bytes"] and hashlib.sha256(raw).hexdigest() == batch["sha256"], "Batch checksum mismatch")
                records = [json.loads(line) for line in raw.splitlines()]
                require(len(records) == batch["records"], "Batch record count mismatch")
                for record in records:
                    require(not validate_record(record, universe), "Invalid research record")
                    require(record["source"] == "sec_edgar" and record["dataset"] == "filings" and record["run_id"] == page["run_id"], "Record is outside page scope")
                    require(record["universe_version"] == universe["universe_version"], "Record universe mismatch")
                    payload = record["payload"]
                    require(payload["accession_number"] == record["source_record_id"], "Accession identity mismatch")
                    require(bool(payload["issuer_rows"]), "Missing issuer evidence")
                    index_forms = sorted({issuer['form'] for issuer in payload['issuer_rows']})
                    require(payload['form'] == ' / '.join(index_forms), "Issuer form summary mismatch")
                    if len(index_forms) > 1:
                        require(payload.get('index_forms') == index_forms, "Missing multi-form evidence")
                    for issuer in payload["issuer_rows"]:
                        item = (record["source_record_id"],) + tuple(issuer[k] for k in ("cik", "company_name", "form", "filing_date", "filename"))
                        require(evidence_identity(item) in evidence, "Filing is not present in pinned source evidence")
                        require(issuer["filing_date"] == payload["filing_date"], "Issuer date/form mismatch")
                    identity = record["observation_id"]
                    require(identity not in run_ids, "Duplicate observation within final manifest")
                    run_ids.add(identity)
                    if identity not in entries:
                        entries[identity] = {"record": record, "manifests": set(), "batches": set(), "snapshots": set()}
                    entry = entries[identity]
                    require(entry["record"] == record, "Conflicting observation identity")
                    entry["manifests"].add(key)
                    entry["batches"].add(batch["key"])
                    entry["snapshots"].add(snapshot["key"])
                page_count += len(records)
            require(page_count == page["record_count"], "Page count mismatch")
            count += page_count
        require(count == manifest["record_count"] == manifest["expected_records"], "Final record count mismatch")
        inputs.append({"key": key, "sha256": hashlib.sha256(body).hexdigest(), "records": count})
    return entries, next(iter(universes.values())), inputs


def semantic_id(record):
    # Preserve matching, timestamp, and payload changes as separate versions.
    ignored = {"observation_id", "run_id", "ingested_at"}
    return "ver_" + digest({k: v for k, v in record.items() if k not in ignored})


def observed_order(record):
    return parse_instant(record["ingested_at"]), record["observation_id"]


def curate(entries, universe):
    tables = {name: [] for name in SCHEMAS}
    by_record = defaultdict(list)
    for observation_id, entry in sorted(entries.items()):
        record = entry["record"]
        version_id = semantic_id(record)
        by_record[record["record_id"]].append(record)
        tables["sec_observations"].append({"observation_id": observation_id,
            "record_id": record["record_id"], "version_id": version_id, "run_id": record["run_id"],
            "ingested_at": record["ingested_at"], "payload_hash": record["payload_hash"],
            "source_manifest_keys": sorted(entry["manifests"]), "raw_batch_keys": sorted(entry["batches"]),
            "source_snapshot_keys": sorted(entry["snapshots"]), "record_json": json_text(record)})
    for record_id, observations in sorted(by_record.items()):
        versions = defaultdict(list)
        for record in observations:
            versions[semantic_id(record)].append(record)
        latest = max(observations, key=observed_order)
        latest_version = semantic_id(latest)
        for version_id, members in sorted(versions.items()):
            representative = max(members, key=observed_order)
            payload = representative["payload"]
            available = representative["available_at"] or {}
            row = {"record_id": record_id, "version_id": version_id,
                "accession_number": representative["source_record_id"], "form": payload["form"],
                "filing_date": date.fromisoformat(payload["filing_date"]), "source_url": representative["source_url"],
                "issuer_ciks": sorted({x["cik"] for x in payload["issuer_rows"]}),
                "issuer_rows_json": json_text(payload["issuer_rows"]), "document_urls": payload["document_urls"],
                "entity_match_status": representative["entity_match_status"],
                "available_at": available.get("value"), "availability_precision": available.get("precision"),
                "availability_basis": representative["availability_basis"],
                "universe_version": representative["universe_version"], "payload_hash": representative["payload_hash"],
                "payload_json": json_text(payload), "first_observed_at": min(members, key=observed_order)["ingested_at"],
                "last_observed_at": representative["ingested_at"], "observation_count": len(members)}
            tables["sec_filing_versions"].append(row)
            if version_id == latest_version:
                tables["sec_filings"].append({**row, "version_count": len(versions),
                    "first_observed_at": min(observations, key=observed_order)["ingested_at"],
                    "last_observed_at": latest["ingested_at"], "observation_count": len(observations)})
        confirmed = set(latest["company_ids"])
        candidates = set(latest["payload"]["candidate_company_ids"]) - confirmed
        for status, ids, basis in [("confirmed", confirmed, latest["payload"]["company_match_basis"]),
                                   ("candidate", candidates, latest["payload"]["candidate_match_basis"])]:
            for company_id in sorted(ids):
                tables["sec_filing_companies"].append({"record_id": record_id, "version_id": latest_version,
                    "company_id": company_id, "match_status": status, "match_basis": basis})
    for company in sorted(universe["companies"], key=lambda c: c["company_id"]):
        tables["companies"].append({k: company[k] for k in ("company_id", "canonical_name", "entity_type",
            "review_status", "collection_enabled", "observed_at")} | {
                "universe_version": universe["universe_version"], "company_json": json_text(company)})
        for sector in company["sectors"]:
            tables["company_sectors"].append({"company_id": company["company_id"],
                **{k: sector[k] for k in ("sector_id", "subsector_ids", "review_status", "classification_basis", "observed_at")},
                "valid_from": date.fromisoformat(sector["valid_from"]) if sector["valid_from"] else None,
                "valid_to": date.fromisoformat(sector["valid_to"]) if sector["valid_to"] else None,
                "evidence_json": json_text(sector["evidence"])})
    return tables


def sector_counts(tables):
    groups = defaultdict(set)
    for link in tables["sec_filing_companies"]:
        for sector in tables["company_sectors"]:
            if sector["company_id"] == link["company_id"] and sector["review_status"] != "rejected":
                groups[sector["sector_id"]].add(link["record_id"])
    return {k: len(v) for k, v in sorted(groups.items())}


def validation_queries(database):
    prefix = database + "."
    return {
        "table_counts": " UNION ALL ".join(f"SELECT '{name}' AS table_name, count(*) AS row_count FROM {prefix}{name}" for name in SCHEMAS) + " ORDER BY table_name",
        "sector_counts": f"SELECT s.sector_id, count(DISTINCT f.record_id) AS filings FROM {prefix}sec_filing_companies f JOIN {prefix}company_sectors s ON f.company_id=s.company_id WHERE s.review_status <> 'rejected' GROUP BY s.sector_id ORDER BY s.sector_id",
        "filing_quality": f"SELECT count(*) AS filings, count(DISTINCT record_id) AS distinct_filings, sum(observation_count) AS observations, count(available_at) AS known_availability FROM {prefix}sec_filings",
        "match_counts": f"SELECT match_status, count(*) AS links FROM {prefix}sec_filing_companies GROUP BY match_status ORDER BY match_status",
        "preview": f"SELECT f.accession_number, f.form, f.filing_date, c.canonical_name, l.match_status, f.available_at FROM {prefix}sec_filings f JOIN {prefix}sec_filing_companies l ON f.record_id=l.record_id JOIN {prefix}companies c ON l.company_id=c.company_id ORDER BY f.accession_number, c.canonical_name"
    }


def validate_config(config):
    require(re.fullmatch(r"[a-z][a-z0-9_]*", config["database"]), "Unsafe database name")
    require(re.fullmatch(r"[a-z][a-z0-9-]*", config["workgroup"]), "Unsafe workgroup name")
    checked_key(config["curated_prefix"])
    checked_key(config["query_results_prefix"])


def prepare(store, settings, config, output_root):
    validate_config(config)
    entries, universe, inputs = read_inputs(store, config["source_manifests"])
    tables = curate(entries, universe)
    del entries
    release_id = digest({"version": VERSION, "arrow": pa.__version__, "inputs": inputs,
        "schema": SCHEMAS, "config": config, "bucket": settings.s3_bucket, "prefix": settings.s3_prefix})
    root = Path(output_root) / release_id
    root.mkdir(parents=True, exist_ok=True)
    release_prefix = f"{config['curated_prefix']}/{release_id}"
    s3_root = f"s3://{settings.s3_bucket}/{settings.s3_prefix}/{release_prefix}"
    files, ddl = {}, [f"CREATE DATABASE IF NOT EXISTS {config['database']};"]
    for name, rows in tables.items():
        schema = pa.schema([(field, ARROW_TYPES[kind]) for field, kind in SCHEMAS[name]])
        path = root / "tables" / name / "part-00000.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        with pq.ParquetWriter(path, schema, compression="snappy", version="1.0") as writer:
            for start in range(0, len(rows), 256):
                writer.write_table(pa.Table.from_pylist(rows[start:start + 256], schema=schema))
        offset = 0
        for batch in pq.ParquetFile(path).iter_batches(batch_size=256, use_threads=False):
            expected_batch = pa.Table.from_pylist(rows[offset:offset + batch.num_rows], schema=schema)
            require(pa.Table.from_batches([batch]).equals(expected_batch), f"Parquet round-trip mismatch: {name}")
            offset += batch.num_rows
        require(offset == len(rows), f"Parquet row count mismatch: {name}")
        from streaming_release import file_digest
        checksum, size = file_digest(path)
        relative = path.relative_to(root).as_posix()
        files[name] = {"path": relative, "sha256": checksum, "bytes": size,
            "rows": len(rows), "location": f"{s3_root}/tables/{name}/", "columns": SCHEMAS[name]}
        columns = ",\n  ".join(f"{field} {kind}" for field, kind in SCHEMAS[name])
        ddl.append(f"CREATE EXTERNAL TABLE {config['database']}.{name} (\n  {columns}\n)\nSTORED AS PARQUET\nLOCATION '{files[name]['location']}'\nTBLPROPERTIES ('classification'='parquet', 'optima_release_id'='{release_id}');")
    queries = validation_queries(config["database"])
    (root / "tables.sql").write_text("\n\n".join(ddl) + "\n")
    (root / "queries.sql").write_text("\n\n".join(f"-- {name}\n{sql};" for name, sql in queries.items()) + "\n")
    match_counts = defaultdict(int)
    for link in tables["sec_filing_companies"]:
        match_counts[link["match_status"]] += 1
    expected = {
        "table_counts": [[name, str(len(rows))] for name, rows in sorted(tables.items())],
        "sector_counts": [[name, str(count)] for name, count in sector_counts(tables).items()],
        "filing_quality": [[str(len(tables["sec_filings"])), str(len(tables["sec_filings"])),
            str(len(tables["sec_observations"])) if tables['sec_filings'] else None,
            str(sum(r["available_at"] is not None for r in tables["sec_filings"]))]],
        "match_counts": [[status, str(count)] for status, count in sorted(match_counts.items())]}
    report = {"streaming_upload": True, "curator_version": VERSION, "release_id": release_id, "release_prefix": release_prefix,
        "bucket": settings.s3_bucket, "s3_prefix": settings.s3_prefix, "config": config,
        "inputs": inputs, "universe_hash": digest(universe), "files": files, "expected_results": expected,
        "queries": queries, "status": "locally_validated", "schema_version": "1.0",
        "semantics": "Latest observed state within selected manifests; not historical point-in-time features."}
    (root / "release.json").write_bytes(canonical_json(report) + b"\n")
    print(json.dumps({"stage": "prepared", "directory": str(root), "expected_results": expected}), flush=True)
    return root


def publish(store, settings, directory):
    root = Path(directory)
    report = load_json(root / "release.json")
    require(report["bucket"] == settings.s3_bucket and report["s3_prefix"] == settings.s3_prefix, "Release destination mismatch")
    if report.get('streaming_upload'):
        from streaming_release import publish as streaming_publish
        streaming_publish(store, root, report)
        return
    # Validate all local artifacts before any upload; marker is written last.
    for info in report["files"].values():
        raw = (root / checked_key(info["path"])).read_bytes()
        require(len(raw) == info["bytes"] and hashlib.sha256(raw).hexdigest() == info["sha256"], "Local release changed after validation")
    for info in report["files"].values():
        key = report["release_prefix"] + "/" + info["path"]
        raw = (root / info["path"]).read_bytes()
        write_checked(store, key, raw, content_type="application/vnd.apache.parquet")
        require(get_bytes(store, key) == raw, "Uploaded Parquet read-back mismatch")
    for name in ("tables.sql", "queries.sql", "release.json"):
        write_checked(store, report["release_prefix"] + "/" + name, (root / name).read_bytes())
    print(json.dumps({"stage": "published", "s3_release": f"s3://{settings.s3_bucket}/{settings.s3_prefix}/{report['release_prefix']}/"}), flush=True)


def run_query(athena, report, sql):
    config = report["config"]
    result = athena.start_query_execution(QueryString=sql,
        QueryExecutionContext={"Database": config["database"], "Catalog": "AwsDataCatalog"},
        WorkGroup=config["workgroup"])
    query_id = result["QueryExecutionId"]
    print(json.dumps({"query_started": query_id}), flush=True)
    deadline = time.monotonic() + 180
    while True:
        execution = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
        status = execution["Status"]["State"]
        if status in {"FAILED", "CANCELLED"}:
            raise RuntimeError(f"Athena {query_id}: {execution['Status'].get('StateChangeReason', status)}")
        if status == "SUCCEEDED":
            break
        if time.monotonic() >= deadline:
            athena.stop_query_execution(QueryExecutionId=query_id)
            raise RuntimeError(f"Athena query timed out: {query_id}")
        time.sleep(1)
    rows = []
    for page in athena.get_paginator("get_query_results").paginate(QueryExecutionId=query_id):
        rows.extend([[v.get("VarCharValue") for v in row["Data"]] for row in page["ResultSet"]["Rows"]])
    return {"query_id": query_id, "bytes_scanned": execution["Statistics"].get("DataScannedInBytes", 0), "rows": rows[1:]}


def deploy(store, settings, directory, update_existing=False):
    import boto3
    from botocore.exceptions import ClientError
    root = Path(directory)
    report = load_json(root / "release.json")
    require(report["bucket"] == settings.s3_bucket and report["s3_prefix"] == settings.s3_prefix, "Release destination mismatch")
    require(get_bytes(store, report["release_prefix"] + "/release.json") == (root / "release.json").read_bytes(), "Publish and validate the release first")
    config, release_id = report["config"], report["release_id"]
    catalog_owner = report.get("catalog_owner", "sec")
    description = report.get("workgroup_description", "Optima SEC pilot")
    validate_config(config)
    session = boto3.Session(region_name=config["region"])
    glue, athena = session.client("glue"), session.client("athena")
    try:
        database = glue.get_database(Name=config["database"])["Database"]
        require(database.get("Parameters", {}).get("optima_pilot") == catalog_owner, "Existing database is not this pilot")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "EntityNotFoundException":
            raise
        glue.create_database(DatabaseInput={"Name": config["database"],
            "Description": description + ". Provisional company matches; not point-in-time training data.",
            "Parameters": {"optima_pilot": catalog_owner}})
    for name, info in report["files"].items():
        columns = [{"Name": field, "Type": kind} for field, kind in info["columns"]]
        definition = {"Name": name, "TableType": "EXTERNAL_TABLE",
            "Parameters": {"EXTERNAL": "TRUE", "classification": "parquet", "optima_release_id": release_id},
            "StorageDescriptor": {"Columns": columns, "Location": info["location"],
                "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                "SerdeInfo": {"SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"}}}
        try:
            existing = glue.get_table(DatabaseName=config["database"], Name=name)["Table"]
            matches=(existing.get("Parameters", {}).get("optima_release_id") == release_id and
                existing["StorageDescriptor"]["Location"] == info["location"] and
                existing["StorageDescriptor"]["Columns"] == columns)
            if not matches:
                require(update_existing and existing.get("Parameters", {}).get("classification") == "parquet" and
                    existing.get("Parameters", {}).get("optima_release_id"), "Existing table conflicts with release: " + name)
                glue.update_table(DatabaseName=config["database"],TableInput=definition,SkipArchive=False)
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "EntityNotFoundException":
                raise
            glue.create_table(DatabaseName=config["database"], TableInput=definition)
    output = f"s3://{report['bucket']}/{report['s3_prefix']}/{config['query_results_prefix']}/"
    try:
        workgroup = athena.get_work_group(WorkGroup=config["workgroup"])["WorkGroup"]
        wc = workgroup["Configuration"]
        require(workgroup.get("Description") == description and workgroup["State"] == "ENABLED" and
            wc["ResultConfiguration"]["OutputLocation"].rstrip("/") == output.rstrip("/") and
            wc.get("EnforceWorkGroupConfiguration") and wc.get("BytesScannedCutoffPerQuery") == 104857600,
            "Existing workgroup conflicts with pilot configuration")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "InvalidRequestException" or "not found" not in exc.response["Error"]["Message"].lower():
            raise
        athena.create_work_group(Name=config["workgroup"], Description=description, Configuration={
            "ResultConfiguration": {"OutputLocation": output, "EncryptionConfiguration": {"EncryptionOption": "SSE_S3"}},
            "EnforceWorkGroupConfiguration": True, "BytesScannedCutoffPerQuery": 104857600,
            "EngineVersion": {"SelectedEngineVersion": "Athena engine version 3"}})
    verification = {"release_id": release_id, "database": config["database"], "workgroup": config["workgroup"], "queries": {}}
    for name, sql in report["queries"].items():
        result = run_query(athena, report, sql)
        verification["queries"][name] = result
        (root / "athena-verification.json").write_text(json.dumps(verification, indent=2) + "\n")
        if name in report["expected_results"]:
            require(result["rows"] == report["expected_results"][name], f"Athena result mismatch: {name}: {result['rows']}")
    verification["status"] = "verified"
    raw = canonical_json(verification) + b"\n"
    (root / "athena-verification.json").write_bytes(raw)
    write_checked(store, f"{report['release_prefix']}/verifications/{hashlib.sha256(raw).hexdigest()}.json", raw)
    print(json.dumps(verification), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "publish", "deploy"))
    parser.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    parser.add_argument("--config", type=Path, default=ROOT / "config/sec-athena-pilot.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "athena-pilot-build")
    parser.add_argument("--release-dir", type=Path)
    parser.add_argument("--update-existing", action="store_true", help="advance owned Glue tables to this immutable release")
    args = parser.parse_args()
    settings = StorageSettings.load(args.storage_config)
    require(settings.backend == "s3", "CLI pilot requires an explicit S3 destination")
    store = settings.store()
    if args.stage == "prepare":
        prepare(store, settings, load_json(args.config), args.output_root)
    else:
        require(args.release_dir is not None, "--release-dir is required")
        if args.stage == "publish":
            publish(store, settings, args.release_dir)
        else:
            deploy(store, settings, args.release_dir, args.update_existing)


if __name__ == "__main__":
    main()
