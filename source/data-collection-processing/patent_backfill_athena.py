#!/usr/bin/env python3
"""Review one complete patent month and publish it as a versioned Athena partition."""
import argparse
import base64
from collections import Counter
from datetime import date
import fcntl
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from collection_storage import StorageSettings, now, write_checked
from patent_adjudication import Reviewer, POLICY_PATH
from patent_athena import publish
from regulatory_athena import read_inputs
from research_contract import ROOT, canonical_json, digest, load_json
import sec_athena_pilot as release

VERSION = "patent-backfill-athena-1.0"
TABLE = "patent_backfill_records"
OWNER = "optima_patent_backfill_v1"
TEXT = ["row_type", "release_id", "observation_id", "record_id", "publication_number",
    "application_number", "family_id", "publication_authority", "kind_code", "title",
    "source_url", "source_manifest", "source_payload_hash", "source_evidence_json",
    "party_reviews_json", "supported_technology_json", "pending_technology_json",
    "ingested_at", "available_at", "current_ownership_status", "universe_hash", "policy_hash", "coverage_note"]
SCHEMA = [(x, "string") for x in TEXT] + [(x, "date") for x in
    ("publication_date", "filing_date", "priority_date", "window_start", "window_end_exclusive")] + [
    (x, "array<string>") for x in ("reported_company_names", "supported_sector_ids", "supported_company_ids", "review_reasons", "cpc_codes")] + [
    ("point_in_time_eligible", "boolean")] + [(x, "bigint") for x in
    ("publications", "supported_technology_publications", "supported_name_publications", "unresolved_party_publications")]
NOTE = "Complete collected query window, not a census. CPC-supported technology and registry-supported names are separate from ownership. Current source observations do not establish historical model availability."


def prepare(store, settings, config, manifest_key, output_root):
    release.validate_config(config)
    manifest = json.loads(release.get_bytes(store, manifest_key))
    task = manifest["task"]
    universe = json.loads(release.get_bytes(store, f"manifests/configurations/universe/{task['universe_hash']}.json"))
    inputs = [{"key": manifest_key, "sha256": hashlib.sha256(release.get_bytes(store, manifest_key)).hexdigest(), "records": manifest["record_count"]}]
    start, end = (date.fromisoformat(task["window"][n][:10]) for n in ("start", "end"))
    following = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    release.require(start.day == 1 and start < end <= following and task["scope"]["date_basis"] == "publication_date", "Require one publication-month window")
    release.require(task["mode"] == "historical", "Require historical patent input")
    rules_hash = task["scope"]["classification_hash"]
    discovery = json.loads(release.get_bytes(store, f"manifests/configurations/patent_classification/{rules_hash}.json"))
    release.require(digest(discovery) == rules_hash, "Discovery rules hash mismatch")
    policy = load_json(POLICY_PATH)
    artifacts = {"policy.json": canonical_json(policy) + b"\n", "universe.json": canonical_json(universe) + b"\n", "input-manifest.json": canonical_json(manifest) + b"\n"}
    artifact_meta = {n: {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)} for n, b in artifacts.items()}
    identity = digest({"encoding": "streaming-row-groups-v2", "version": VERSION, "arrow": pa.__version__, "inputs": inputs, "schema": SCHEMA,
        "artifacts": artifact_meta, "config": config, "bucket": settings.s3_bucket, "prefix": settings.s3_prefix})
    reviewer = Reviewer(universe, policy)
    publications, counts, authorities, sectors, review_rows = set(), Counter(), Counter(), Counter(), Counter()
    root = Path(output_root) / identity
    path = root / "tables" / TABLE / "part-00000.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = pa.schema([(f, release.ARROW_TYPES[t]) for f, t in SCHEMA])
    writer = pq.ParquetWriter(path, schema, compression="snappy", version="1.0", use_dictionary=False)
    buffer = []
    buffer_bytes = 0
    expected_hash = hashlib.sha256()
    def normalized(row):
        return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in row.items()}
    def flush():
        nonlocal buffer_bytes
        if buffer:
            table = pa.Table.from_pylist(buffer, schema=schema)
            for row in table.to_pylist():
                expected_hash.update(canonical_json(normalized(row)) + b"\n")
            writer.write_table(table, row_group_size=64)
            buffer.clear()
            buffer_bytes = 0
    def append(row):
        nonlocal buffer_bytes
        buffer.append(row)
        buffer_bytes += len(canonical_json(normalized(row)))
        if len(buffer) >= 64 or buffer_bytes >= 2 * 1024 * 1024:
            flush()
    common = {"release_id": identity, "source_manifest": manifest_key, "universe_hash": digest(universe),
        "policy_hash": digest(policy), "window_start": start, "window_end_exclusive": end,
        "coverage_note": NOTE, "current_ownership_status": "not_established", "point_in_time_eligible": False}
    def consume(entry):
        record = entry["record"]
        data = record["payload"]["data"]
        decision = reviewer.decide(record)
        review_rows["party"] += len(decision["reported_parties"])
        review_rows["sector"] += len(decision["supported_technology"]) + len(decision["pending_technology"])
        pub = data["publication_number"]
        release.require(pub not in publications and start.isoformat() <= data["publication_date"] < end.isoformat(), "Duplicate or out-of-window publication")
        publications.add(pub)
        counts["publications"] += 1
        counts["supported_technology_publications"] += bool(decision["research_sector_ids"])
        counts["supported_name_publications"] += bool(decision["reported_party_company_ids"])
        counts["unresolved_party_publications"] += not decision["reported_parties"] or any(p["status"] != "registry_name_supported" for p in decision["reported_parties"])
        authorities[data["country_code"]] += 1
        sectors.update(decision["research_sector_ids"])
        append({**common, "row_type": "publication", "observation_id": record["observation_id"],
            "record_id": record["record_id"], **{k: data.get(k) for k in ("publication_number", "application_number", "family_id", "kind_code", "title", "cpc_codes")},
            "publication_authority": data["country_code"], "source_url": record["source_url"],
            "source_payload_hash": record["payload_hash"], "source_evidence_json": release.json_text(record["payload"]["source_evidence"]),
            "party_reviews_json": release.json_text(decision["reported_parties"]),
            "supported_technology_json": release.json_text(decision["supported_technology"]),
            "pending_technology_json": release.json_text(decision["pending_technology"]),
            "reported_company_names": sorted(set(data["assignees"] + data["applicants"])),
            "supported_sector_ids": decision["research_sector_ids"], "supported_company_ids": decision["reported_party_company_ids"],
            "review_reasons": decision["review_reasons"], "ingested_at": record["ingested_at"], "available_at": None,
            **{k: date.fromisoformat(data[k]) if data.get(k) else None for k in ("publication_date", "filing_date", "priority_date")}})
    count_fields = ("publications", "supported_technology_publications", "supported_name_publications", "unresolved_party_publications")
    try:
        _, checked_universe, checked_inputs = read_inputs(store, [manifest_key],
            allowed={"google_patents_bigquery"}, dataset="patent_records", consume=consume)
        release.require(checked_inputs == inputs and checked_universe == universe, "Input changed during curation")
        append({**common, "row_type": "coverage", **{k: counts[k] for k in count_fields}})
        flush()
    finally:
        writer.close()
    actual_hash = hashlib.sha256(); actual_count = 0
    for batch in pq.ParquetFile(path).iter_batches(batch_size=64, use_threads=False):
        for row in batch.to_pylist():
            actual_hash.update(canonical_json(normalized(row)) + b"\n")
            actual_count += 1
    release.require(actual_count == counts["publications"] + 1 and actual_hash.digest() == expected_hash.digest(), "Parquet round-trip mismatch")
    prefix = config["curated_prefix"] + "/" + identity
    from streaming_release import file_digest
    checksum, size = file_digest(path)
    files = {TABLE: {"path": str(path.relative_to(root)), "sha256": checksum,
        "bytes": size, "rows": actual_count, "columns": SCHEMA,
        "location": f"s3://{settings.s3_bucket}/{settings.s3_prefix}/{prefix}/tables/{TABLE}/"}}
    for name, body in artifacts.items():
        (root / "artifacts").mkdir(exist_ok=True)
        (root / "artifacts" / name).write_bytes(body)
    report = {"streaming_upload": True, "release_id": identity, "version": VERSION, "release_prefix": prefix, "config": config,
        "bucket": settings.s3_bucket, "s3_prefix": settings.s3_prefix, "files": files, "artifacts": artifact_meta,
        "publication_month": start.strftime("%Y-%m"), "window_start": str(start), "window_end_exclusive": str(end),
        "inputs": inputs, "counts": {k: counts[k] for k in count_fields}, "authorities": dict(authorities),
        "supported_sectors": dict(sectors), "review_rows": {k: review_rows[k] for k in ("party", "sector")}, "universe_hash": digest(universe), "policy_hash": digest(policy),
        "status": "locally_validated", "ownership_verified": False, "point_in_time_eligible": False}
    (root / "release.json").write_bytes(canonical_json(report) + b"\n")
    (root / "tables.sql").write_text("-- Catalog schema managed by patent_backfill_athena.py\n")
    (root / "queries.sql").write_text("\n\n".join(views(config["database"]).values()) + "\n")
    print(json.dumps({"directory": str(root), "counts": report["counts"], "supported_sectors": report["supported_sectors"]}), flush=True)
    return root


def views(db):
    base = f"{db}.{TABLE}"
    omitted = {"row_type", "publications", "supported_technology_publications", "supported_name_publications", "unresolved_party_publications"}
    columns = ", ".join([f for f, _ in SCHEMA if f not in omitted] + ["publication_month"])
    return {
        "patent_backfill_publications": f"SELECT {columns} FROM {base} WHERE row_type='publication'",
        "patent_backfill_coverage": f"SELECT publication_month, release_id, window_start, window_end_exclusive, publications, supported_technology_publications, supported_name_publications, unresolved_party_publications, universe_hash, policy_hash, source_manifest, coverage_note FROM {base} WHERE row_type='coverage'",
        "patent_backfill_party_reviews": f"SELECT publication_month, release_id, publication_number, json_extract_scalar(p, '$.reported_name') reported_name, json_extract_scalar(p, '$.role') party_role, json_extract_scalar(p, '$.status') review_status, json_extract_scalar(p, '$.company_id') company_id, json_extract_scalar(p, '$.reason') reason, json_format(p) evidence_json FROM {base} CROSS JOIN UNNEST(CAST(json_parse(party_reviews_json) AS array(json))) AS t(p) WHERE row_type='publication'",
        "patent_backfill_sector_reviews": f"SELECT publication_month, release_id, publication_number, json_extract_scalar(s, '$.sector_id') sector_id, json_extract_scalar(s, '$.category') category, 'supported' review_status, json_format(s) evidence_json FROM {base} CROSS JOIN UNNEST(CAST(json_parse(supported_technology_json) AS array(json))) AS t(s) WHERE row_type='publication' UNION ALL SELECT publication_month, release_id, publication_number, json_extract_scalar(s, '$.sector_id') sector_id, json_extract_scalar(s, '$.category') category, 'pending' review_status, json_format(s) evidence_json FROM {base} CROSS JOIN UNNEST(CAST(json_parse(pending_technology_json) AS array(json))) AS t(s) WHERE row_type='publication'"}


def descriptor(location):
    return {"Columns": [{"Name": n, "Type": t} for n, t in SCHEMA], "Location": location,
        "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
        "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
        "SerdeInfo": {"SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"}}


def view_input(view, sql):
    """Recover a crash after Athena creates a view but before its hash is tagged."""
    marker = view.get("Parameters", {}).get("optima_view_hash")
    if marker is None:
        encoded = view.get("ViewOriginalText", "")
        prefix, suffix = "/* Presto View: ", " */"
        release.require(encoded.startswith(prefix) and encoded.endswith(suffix), "Unowned view has unsupported definition")
        original = json.loads(base64.b64decode(encoded[len(prefix):-len(suffix)], validate=True))
        release.require(same_sql(original.get("originalSql", ""), sql), "Unowned view SQL differs")
    else:
        release.require(marker == digest(sql), "Existing view SQL version conflicts")
    release.require(view.get("TableType") == "VIRTUAL_VIEW", "Existing object is not a view")
    allowed = {k: view[k] for k in ("Name", "Description", "Owner", "Retention", "StorageDescriptor", "PartitionKeys", "ViewOriginalText", "ViewExpandedText", "TableType", "Parameters") if k in view}
    allowed["Parameters"] = {**allowed.get("Parameters", {}), "optima_view_hash": digest(sql)}
    return allowed


def same_sql(left, right):
    from sqlglot import parse_one, exp
    def without_parenthesis(node):
        while isinstance(node, exp.Paren):
            node = node.this
        return node
    # Removing Paren nodes retains the expression tree's operator grouping.
    # It does not strip parentheses from raw strings or change string literals.
    def normalized(sql):
        tree = parse_one(sql, read="trino").transform(without_parenthesis)
        for select in tree.find_all(exp.Select):
            source = select.args.get("from")
            wrapped = source.this if source else None
            # Athena wraps the generated CROSS JOIN relation in parentheses.
            # Only flatten this unaliased, all-CROSS form; retain all other joins.
            if isinstance(wrapped, exp.Subquery) and not wrapped.alias and isinstance(wrapped.this, exp.Table) and not select.args.get("joins"):
                table = wrapped.this
                joins = table.args.get("joins", [])
                if joins and all(j.kind == "CROSS" and not j.args.get("on") and not j.args.get("using") for j in joins):
                    table.set("joins", None)
                    wrapped.replace(table)
                    select.set("joins", joins)
        return tree
    return normalized(left) == normalized(right)


def deploy(store, settings, root, replace_window=False, clients=None):
    import boto3
    from botocore.exceptions import ClientError
    root = Path(root)
    report = load_json(root / "release.json")
    release.require(report["bucket"] == settings.s3_bucket and report["s3_prefix"] == settings.s3_prefix, "Destination mismatch")
    release.require(release.get_bytes(store, report["release_prefix"] + "/release.json") == (root / "release.json").read_bytes(), "Publish release first")
    config = report["config"]
    release.validate_config(config)
    if clients is None:
        session = boto3.Session(region_name=config["region"])
        clients = session.client("glue"), session.client("athena")
    glue, athena = clients
    db = config["database"]
    release.require(glue.get_database(Name=db)["Database"].get("Parameters", {}).get("optima_pilot") == "patents", "Patent database ownership mismatch")
    wg = athena.get_work_group(WorkGroup=config["workgroup"])["WorkGroup"]
    wc = wg["Configuration"]
    release.require(wg["State"] == "ENABLED" and wc.get("EnforceWorkGroupConfiguration") and wc.get("BytesScannedCutoffPerQuery") == 104857600, "Workgroup safety configuration mismatch")
    empty_location = f"s3://{settings.s3_bucket}/{settings.s3_prefix}/curated/patent_backfill/catalog/"
    definition = {"Name": TABLE, "TableType": "EXTERNAL_TABLE", "Parameters": {"classification": "parquet", "optima_owner": OWNER},
        "PartitionKeys": [{"Name": "publication_month", "Type": "string"}], "StorageDescriptor": descriptor(empty_location)}
    try:
        existing = glue.get_table(DatabaseName=db, Name=TABLE)["Table"]
        release.require(existing.get("Parameters", {}).get("optima_owner") == OWNER and existing["StorageDescriptor"]["Columns"] == definition["StorageDescriptor"]["Columns"] and existing["PartitionKeys"] == definition["PartitionKeys"], "Existing backfill table conflicts")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "EntityNotFoundException":
            raise
        glue.create_table(DatabaseName=db, TableInput=definition)
    for name, sql in views(db).items():
        try:
            view = glue.get_table(DatabaseName=db, Name=name)["Table"]
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "EntityNotFoundException":
                raise
            release.run_query(athena, report, f"CREATE VIEW {db}.{name} AS {sql}")
            view = glue.get_table(DatabaseName=db, Name=name)["Table"]
        allowed = view_input(view, sql)
        if view.get("Parameters", {}).get("optima_view_hash") is None:
            glue.update_table(DatabaseName=db, TableInput=allowed)
    month = report["publication_month"]
    previous = None
    try:
        previous = glue.get_partition(DatabaseName=db, TableName=TABLE, PartitionValues=[month])["Partition"]
        release.require(previous.get("Parameters", {}).get("optima_owner") == OWNER, "Partition ownership mismatch")
        release.require(previous["Parameters"].get("release_id") == report["release_id"] or replace_window, "Use --replace-window for reviewed replacement")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "EntityNotFoundException":
            raise
    partition = {"Values": [month], "StorageDescriptor": descriptor(report["files"][TABLE]["location"]),
        "Parameters": {"optima_owner": OWNER, "release_id": report["release_id"]}}
    queries = {
        "publications": f"SELECT count(*), count(DISTINCT publication_number), count(available_at), count_if(point_in_time_eligible), count_if(current_ownership_status <> 'not_established'), count_if(publication_date < DATE '{report['window_start']}' OR publication_date >= DATE '{report['window_end_exclusive']}'), count_if(release_id <> '{report['release_id']}') FROM {db}.patent_backfill_publications WHERE publication_month='{month}'",
        "coverage": f"SELECT publications, supported_technology_publications, supported_name_publications, unresolved_party_publications FROM {db}.patent_backfill_coverage WHERE publication_month='{month}'",
        "sectors": f"SELECT sector, count(*) FROM {db}.patent_backfill_publications CROSS JOIN UNNEST(supported_sector_ids) t(sector) WHERE publication_month='{month}' GROUP BY sector ORDER BY sector",
        "review_views": f"SELECT 'party' AS kind, count(*) AS records FROM {db}.patent_backfill_party_reviews WHERE publication_month='{month}' UNION ALL SELECT 'sector', count(*) FROM {db}.patent_backfill_sector_reviews WHERE publication_month='{month}' ORDER BY kind"}
    count = str(report["counts"]["publications"])
    expected = {"publications": [[count, count, "0", "0", "0", "0", "0"]],
        "coverage": [[str(report["counts"][k]) for k in ("publications", "supported_technology_publications", "supported_name_publications", "unresolved_party_publications")]],
        "sectors": [[s, str(n)] for s, n in sorted(report["supported_sectors"].items())],
        "review_views": [[k, str(n)] for k, n in sorted(report["review_rows"].items())]}
    verification = {"release_id": report["release_id"], "publication_month": month, "checked_at": now(), "queries": {}}
    try:
        if previous:
            glue.update_partition(DatabaseName=db, TableName=TABLE, PartitionValueList=[month], PartitionInput=partition)
        else:
            glue.create_partition(DatabaseName=db, TableName=TABLE, PartitionInput=partition)
        for name, sql in queries.items():
            result = release.run_query(athena, report, sql)
            verification["queries"][name] = result
            if name in expected:
                release.require(result["rows"] == expected[name], "Athena verification mismatch: " + name)
        verification["status"] = "verified"
        body = canonical_json(verification) + b"\n"
        write_checked(store, report["release_prefix"] + "/verifications/" + hashlib.sha256(body).hexdigest() + ".json", body)
        (root / "athena-verification.json").write_bytes(body)
    except Exception:
        if previous:
            original = {k: previous[k] for k in ("Values", "StorageDescriptor", "Parameters", "LastAccessTime", "LastAnalyzedTime") if k in previous}
            glue.update_partition(DatabaseName=db, TableName=TABLE, PartitionValueList=[month], PartitionInput=original)
        else:
            glue.delete_partition(DatabaseName=db, TableName=TABLE, PartitionValues=[month])
        raise
    print(json.dumps(verification), flush=True)
    return verification


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "publish", "deploy"))
    parser.add_argument("--manifest")
    parser.add_argument("--release-dir", type=Path)
    parser.add_argument("--replace-window", action="store_true")
    parser.add_argument("--config", type=Path, default=ROOT / "config/patent-backfill-athena.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "patent-backfill-athena-build")
    args = parser.parse_args()
    with (ROOT / ".patent-backfill-athena.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        settings = StorageSettings.load(ROOT / "config/collection-storage.s3.json")
        store = settings.store()
        if args.stage == "prepare":
            release.require(args.manifest is not None, "--manifest required")
            prepare(store, settings, load_json(args.config), args.manifest, args.output_root)
        else:
            release.require(args.release_dir is not None, "--release-dir required")
            if args.stage == "publish":
                publish(store, settings, args.release_dir)
            else:
                deploy(store, settings, args.release_dir, args.replace_window)


if __name__ == "__main__":
    main()
