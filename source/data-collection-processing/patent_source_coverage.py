#!/usr/bin/env python3
"""Measure global patent coverage with an estimated, capped and reusable query job."""
import argparse
import csv
from datetime import date, datetime, timezone
import fcntl
import json
from pathlib import Path

from collection_storage import StorageSettings, now, write_json
from patent_bigquery_access import API, response_json, session, verify
from patent_bigquery_collection import BigQuery, decode_row
from research_contract import ROOT, digest


def build(as_of, maximum_bytes):
    if type(maximum_bytes) is not int or maximum_bytes <= 0:
        raise ValueError("maximum_bytes must be a positive integer")
    return {"configuration": {"dryRun": True, "query": {
        "query": (ROOT / "patent_source_coverage.sql").read_text(),
        "useLegacySql": False, "maximumBytesBilled": str(maximum_bytes),
        "parameterMode": "NAMED", "queryParameters": [{"name": "as_of",
            "parameterType": {"type": "DATE"}, "parameterValue": {"value": str(as_of)}}]}},
        "provenance": {"purpose": "source_wide_coverage_not_sector_selection", "as_of": str(as_of)}}


def revision(metadata):
    result = {k: metadata.get(k) for k in ("id", "lastModifiedTime", "numRows", "numBytes")}
    if any(v is None for v in result.values()):
        raise ValueError("missing source revision metadata")
    return result


def check(http, store, plan, execute=False):
    estimate = verify(http, plan)
    before = revision(estimate["source_metadata"])
    identity = digest({"plan": plan, "source_revision": before})
    prefix = f"operations/patents/source-coverage/{identity}"
    result_key = prefix + "/result.json"
    cached = store.get(result_key)
    if execute and cached:
        return {**json.loads(cached.body), "already_complete": True}
    report = {"status": "estimated", "checked_at": now(), "plan": plan,
        "estimate": estimate, "source_revision_before": before,
        "data_query_executed": False, "coverage_id": identity,
        "coverage_note": "Publication-date maxima and row counts do not prove complete country or sector coverage."}
    write_json(store, prefix + f"/estimates/{digest(report)}.json", report)
    if not execute:
        return report
    if not estimate["estimate_within_ceiling"]:
        return {**report, "status": "blocked", "reason": "estimated_scan_exceeds_ceiling"}
    query = {**plan["configuration"]["query"], "useQueryCache": False}
    job_id = "optima_patent_coverage_" + identity
    # Persist deterministic intent before any billed request. A retry obtains
    # the same job; result expiry never silently generates a replacement ID.
    write_json(store, prefix + "/intent.json", {"job_id": job_id, "query": query,
        "source_revision": before, "plan_hash": digest(plan)})
    client = BigQuery(http)
    job = client.job(job_id, query)
    report.update(job_id=job_id, data_query_executed=True)
    if job.get("status", {}).get("errorResult"):
        return {**report, "status": "failed", "reason": "bigquery_job_failed"}
    result = client.page(job_id, None, 1000)
    if result.get("errors"):
        return {**report, "status": "failed", "reason": "bigquery_result_failed"}
    if not result.get("jobComplete"):
        return {**report, "status": "partial", "reason": "bigquery_job_pending"}
    rows = [decode_row(result["schema"]["fields"], row) for row in result.get("rows", [])]
    if result.get("pageToken") or len(rows) != int(result["totalRows"]):
        raise ValueError("coverage aggregate exceeds complete single-page result")
    after = revision(response_json(http.get(API + "/projects/patents-public-data/datasets/patents/tables/publications", timeout=60)))
    job = client.job(job_id, query)
    as_of = date.fromisoformat(plan["provenance"]["as_of"])
    for row in rows:
        for name in ("publications", "missing_or_invalid_dates", "future_dates",
                     "publications_last_90_days", "publications_last_180_days", "publications_last_365_days"):
            row[name] = int(row[name])
        latest = row["latest_publication_date"]
        row["latest_publication_lag_days"] = (as_of - date.fromisoformat(latest)).days if latest else None
    report.update(status="complete" if before == after else "source_changed",
        source_revision_after=after, countries=rows, response=result,
        statistics=job.get("statistics", {}), completed_at=now())
    if before == after and sum(r["publications"] for r in rows) != int(before["numRows"]):
        report.update(status="source_count_mismatch")
    write_json(store, prefix + f"/observations/{digest(report)}.json", report)
    if report["status"] == "complete":
        write_json(store, result_key, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    parser.add_argument("--maximum-bytes-billed", type=int, default=5_000_000_000)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with (ROOT / ".patent-source-coverage.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        store = StorageSettings.load(ROOT / "config/collection-storage.s3.json").store()
        with session(ROOT / "config/google-patents-aws.json") as http:
            report = check(http, store, build(args.as_of, args.maximum_bytes_billed), args.execute)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        if report.get("countries"):
            with args.output.with_suffix(".csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(report["countries"][0]))
                writer.writeheader()
                writer.writerows(report["countries"])
        print(json.dumps({"status": report["status"], "coverage_id": report["coverage_id"],
            "already_complete": report.get("already_complete", False),
            "data_query_executed": report["data_query_executed"],
            "estimated_bytes": report["estimate"]["estimated_bytes_processed"],
            "bytes_billed": report.get("statistics", {}).get("query", {}).get("totalBytesBilled"),
            "authority_count": len(report.get("countries", [])), "output": str(args.output)}))
        return 0 if report["status"] in {"complete", "estimated"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
