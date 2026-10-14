#!/usr/bin/env python3
"""Curate complete news search windows into a bounded, auditable Athena release."""
import argparse
from collections import Counter, defaultdict
import fcntl
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from collection_storage import StorageSettings
from regulatory_athena import read_inputs
from research_contract import ROOT, canonical_json, digest, load_json
import sec_athena_pilot as release

VERSION = "news-athena-1.0"
SCHEMAS = {
    "news_articles": [(n, "string") for n in ("record_id", "source", "provider_id", "source_url", "title", "language", "published_at", "first_observed_at", "last_observed_at", "available_at", "data_json")] +
        [("candidate_sector_ids", "array<string>"), ("observation_count", "bigint"), ("version_count", "bigint"), ("point_in_time_eligible", "boolean")],
    "news_observations": [(n, "string") for n in ("observation_id", "record_id", "version_id", "ingested_at", "record_json")] +
        [("manifest_keys", "array<string>"), ("evidence_keys", "array<string>")],
    "news_company_candidates": [(n, "string") for n in ("record_id", "company_id", "review_status")],
    "news_coverage": [(n, "string") for n in ("source_manifest", "source", "query_target", "language", "window_start", "window_end_exclusive", "mode", "status", "coverage_note")] + [("observations", "bigint")]
}


def prepare(store, settings, config, keys, output_root):
    release.validate_config(config)
    release.require(keys, "At least one complete manifest required")
    entries, universe, inputs = read_inputs(store, keys, allowed={"finlight", "marketaux"}, dataset="news_articles")
    tables = {name: [] for name in SCHEMAS}
    grouped = defaultdict(list)
    for oid, entry in sorted(entries.items()):
        record = entry["record"]
        release.require(record["available_at"] is None, "News historical availability requires separate review")
        version = digest([record["source"], record["source_record_id"], record["payload"]["data"]])
        grouped[record["record_id"]].append((record, version))
        tables["news_observations"].append({"observation_id": oid, "record_id": record["record_id"],
            "version_id": version, "ingested_at": record["ingested_at"], "record_json": release.json_text(record),
            "manifest_keys": sorted(entry["manifests"]),
            "evidence_keys": sorted({e["key"] for e in record["payload"]["source_evidence"]})})
    for rid, members in sorted(grouped.items()):
        latest = max((r for r, _ in members), key=release.observed_order)
        payload = latest["payload"]
        tables["news_articles"].append({"record_id": rid, "source": latest["source"], "provider_id": latest["source_record_id"],
            "source_url": latest["source_url"], "title": payload["title"], "language": payload["data"].get("language"),
            "published_at": latest["event_at"]["value"], "first_observed_at": min(r["ingested_at"] for r, _ in members),
            "last_observed_at": latest["ingested_at"], "available_at": None, "data_json": release.json_text(payload["data"]),
            "candidate_sector_ids": sorted({s for r, _ in members for s in r["payload"]["candidate_sector_ids"]}),
            "observation_count": len(members), "version_count": len({v for _, v in members}), "point_in_time_eligible": False})
        for cid in sorted({c for r, _ in members for c in r["payload"]["candidate_company_ids"]}):
            tables["news_company_candidates"].append({"record_id": rid, "company_id": cid, "review_status": "candidate"})
    for key in sorted(set(keys)):
        manifest = json.loads(release.get_bytes(store, key))
        task, scope = manifest["task"], manifest["task"]["scope"]
        tables["news_coverage"].append({"source_manifest": key, "source": task["source"], "query_target": scope["target"]["name"],
            "language": scope["language"] or "all_provider_languages", "window_start": task["window"]["start"],
            "window_end_exclusive": task["window"]["end"], "mode": task["mode"], "status": "complete_search",
            "observations": manifest["record_count"],
            "coverage_note": "Exhausted specified provider query, not complete global news coverage. Current article versions are not historical model-ready features."})
    identity = digest({"version": VERSION, "arrow": pa.__version__, "inputs": inputs, "schema": SCHEMAS,
        "config": config, "bucket": settings.s3_bucket, "prefix": settings.s3_prefix})
    root, prefix = Path(output_root) / identity, config["curated_prefix"] + "/" + identity
    files, ddl = {}, []
    for name, rows in tables.items():
        table = pa.Table.from_pylist(rows, schema=pa.schema([(n, release.ARROW_TYPES[t]) for n, t in SCHEMAS[name]]))
        relative = f"tables/{name}/part-00000.parquet"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, path, compression="snappy", version="1.0")
        release.require(pq.ParquetFile(path).read().equals(table), "News Parquet round-trip mismatch")
        body = path.read_bytes()
        location = f"s3://{settings.s3_bucket}/{settings.s3_prefix}/{prefix}/tables/{name}/"
        files[name] = {"path": relative, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "rows": len(rows), "columns": SCHEMAS[name], "location": location}
        ddl.append(f"CREATE EXTERNAL TABLE {config['database']}.{name} (" + ", ".join(f"{n} {t}" for n, t in SCHEMAS[name]) + f") STORED AS PARQUET LOCATION '{location}';")
    db = config["database"]
    counts = Counter(r["source"] for r in tables["news_articles"])
    queries = {"table_counts": " UNION ALL ".join(f"SELECT '{n}' AS table_name, count(*) AS records FROM {db}.{n}" for n in SCHEMAS) + " ORDER BY table_name",
        "source_counts": f"SELECT source, count(*) FROM {db}.news_articles GROUP BY source ORDER BY source",
        "quality": f"SELECT count(*), count(DISTINCT record_id), count(available_at), count_if(point_in_time_eligible), COALESCE(sum(observation_count), 0) FROM {db}.news_articles"}
    expected = {"table_counts": [[n, str(len(rows))] for n, rows in sorted(tables.items())],
        "source_counts": [[s, str(n)] for s, n in sorted(counts.items())],
        "quality": [[str(len(grouped)), str(len(grouped)), "0", "0", str(len(entries))]]}
    report = {"curator_version": VERSION, "catalog_owner": "news", "workgroup_description": "Optima news pilot",
        "release_id": identity, "release_prefix": prefix, "bucket": settings.s3_bucket, "s3_prefix": settings.s3_prefix,
        "config": config, "inputs": inputs, "universe_hash": digest(universe), "files": files,
        "queries": queries, "expected_results": expected, "status": "locally_validated"}
    (root / "release.json").write_bytes(canonical_json(report) + b"\n")
    (root / "tables.sql").write_text("\n\n".join(ddl) + "\n")
    (root / "queries.sql").write_text("\n\n".join(queries.values()) + "\n")
    print(json.dumps({"directory": str(root), "expected_results": expected}), flush=True)
    return root


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("prepare", "publish", "deploy"))
    p.add_argument("--collection-report", type=Path)
    p.add_argument("--release-dir", type=Path)
    args = p.parse_args()
    with (ROOT / ".news-athena.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        settings = StorageSettings.load(ROOT / "config/collection-storage.s3.json")
        store = settings.store()
        if args.stage == "prepare":
            release.require(args.collection_report is not None, "--collection-report required")
            report = load_json(args.collection_report)
            release.require(report["status"] == "complete", "Finish the selected cohort first")
            prepare(store, settings, load_json(ROOT / "config/news-athena.json"),
                [r["manifest"] for r in report["results"]], ROOT / "news-athena-build")
        else:
            release.require(args.release_dir is not None, "--release-dir required")
            if args.stage == "publish":
                release.publish(store, settings, args.release_dir)
            else:
                release.deploy(store, settings, args.release_dir)


if __name__ == "__main__":
    main()
