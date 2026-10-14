#!/usr/bin/env python3
"""Run bounded global patent queries and checkpoint their fixed job results to S3."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

from collection_storage import AlreadyComplete, StorageSettings, now, write_checked, write_json
from patent_bigquery_access import API, PROJECT, dry_configuration, response_json, session
from patent_collection import (PatentMatcher, RULES_PATH, SourceIssue, envelope, export_record,
                               outcome, require, start_run)
from patent_query_plan import build
from research_contract import COLLECTION_UNIVERSE, ROOT, canonical_json, digest, load_json


def decode_value(field, value):
    if value is None:
        return None
    if field.get("mode") == "REPEATED":
        scalar = {k: v for k, v in field.items() if k != "mode"}
        return [decode_value(scalar, v["v"]) for v in value]
    if field["type"] == "RECORD":
        return decode_row(field["fields"], value)
    # Keep numeric identifiers as strings rather than converting via floats.
    return value


def decode_row(fields, row):
    require(len(fields) == len(row["f"]), "query_result_schema_mismatch")
    return {field["name"]: decode_value(field, value["v"]) for field, value in zip(fields, row["f"])}


class BigQuery:
    def __init__(self, http):
        self.http = http

    def job(self, identity, query):
        url = API + f"/projects/{PROJECT}/jobs/{identity}"
        response = self.http.get(url, params={"location": "US"}, timeout=60)
        if response.status_code == 404:
            response = self.http.post(API + f"/projects/{PROJECT}/jobs", json={
                "jobReference": {"projectId": PROJECT, "location": "US", "jobId": identity},
                "configuration": {"query": query}}, timeout=60)
            if response.status_code == 409:
                response = self.http.get(url, params={"location": "US"}, timeout=60)
        job = response_json(response)
        actual = job["configuration"]["query"]
        require(all(actual.get(k) == v for k, v in query.items()), "existing_job_configuration_mismatch")
        return job

    def page(self, identity, token, size):
        params = {"location": "US", "maxResults": size, "timeoutMs": 10000}
        if token:
            params["pageToken"] = token
        return response_json(self.http.get(API + f"/projects/{PROJECT}/queries/{identity}", params=params, timeout=60))


def save_evidence(store, value, url):
    body = canonical_json(value)
    checksum = hashlib.sha256(body).hexdigest()
    key = f"source_documents/google_patents_bigquery/{checksum}"
    write_checked(store, key, body)
    return {"key": key, "sha256": checksum, "source_url": url, "retrieved_at": now()}


def query_scope(plan, maximum_bytes, page_size):
    return {"date_basis": "publication_date", "query_plan_hash": digest(plan),
        "query_plan_key": f"manifests/configurations/patent_bigquery/{digest(plan)}.json",
        "maximum_bytes_billed": maximum_bytes, "page_size": page_size,
        "project_id": PROJECT, "location": "US",
        "coverage": "Fixed BigQuery job results for shared-universe names or technology heuristics; source may lag publication."}


def collect(store, settings, universe, taxonomy, plan, maximum_bytes, client,
            page_size=500, max_pages=100, refresh=False):
    require(type(maximum_bytes) is int and maximum_bytes > 0 and
            1 <= page_size <= 1000 and max_pages > 0, "invalid_limits")
    provenance = plan["provenance"]
    start, end = (date.fromisoformat(provenance[k]) for k in ("window_start", "window_end_exclusive"))
    rules = load_json(RULES_PATH)
    config, original_ceiling = dry_configuration(plan)
    require(plan == build(universe, rules, start, end, original_ceiling), "query_plan_configuration_mismatch")
    query = config["query"]
    query["maximumBytesBilled"] = str(maximum_bytes)
    query["useQueryCache"] = True
    plan_key = f"manifests/configurations/patent_bigquery/{digest(plan)}.json"
    write_json(store, plan_key, plan)
    scope = query_scope(plan, maximum_bytes, page_size)
    try:
        run = start_run(store, settings, universe, taxonomy, "google_patents_bigquery",
            start, end, "historical", scope, rules, refresh)
    except AlreadyComplete as exc:
        return {"status": "complete", "already_complete": True, "manifest": str(exc)}
    try:
        if run.exhausted:
            initial = json.loads(run.state["pages"][0]["cursor_after"])
            completed_prefix = f"incoming/patents/google-bigquery/{initial['export_date']}/{initial['job_id']}"
            metadata_object = store.get(completed_prefix + "/export-metadata.json")
            require(metadata_object is not None, "missing_export_metadata")
            require(json.loads(metadata_object.body)["row_count"] == run.state["record_count"], "query_duplicate_records_or_missing_rows")
            return outcome(run, "complete")
        if run.cursor:
            state = json.loads(run.cursor)
        else:
            state = {"job_id": "optima_patents_" + run.run_id.replace("-", "_"),
                     "page_token": None, "offset": 0, "total": None, "export_date": run.started_at[:10]}
            # Commit the job identity BEFORE submitting a potentially billed job.
            # Retry/resume uses this ID rather than accidentally starting twice.
            run.commit_page([], next_cursor=json.dumps(state, sort_keys=True))
        job_id = state["job_id"]
        job = client.job(job_id, query)
        job_ref = save_evidence(store, job, API + f"/projects/{PROJECT}/jobs/{job_id}")
        if job.get("status", {}).get("errorResult"):
            return outcome(run, "failed", "bigquery_job_failed")
        matcher = PatentMatcher(universe)
        prefix = f"incoming/patents/google-bigquery/{state['export_date']}/{job_id}"
        pages = 0
        while not run.exhausted:
            if pages >= max_pages:
                return outcome(run, "partial", "page_limit")
            result = client.page(job_id, state["page_token"], page_size)
            ref = save_evidence(store, result, API + f"/projects/{PROJECT}/queries/{job_id}")
            if result.get("errors"):
                return outcome(run, "failed", "bigquery_query_failed")
            if not result.get("jobComplete"):
                return outcome(run, "partial", "bigquery_job_pending")
            total = int(result["totalRows"])
            require(state["total"] is None or state["total"] == total, "query_result_total_changed")
            rows = [decode_row(result["schema"]["fields"], row) for row in result.get("rows", [])]
            token = result.get("pageToken")
            require((not token or rows) and (not token or token != state["page_token"]), "invalid_query_pagination")
            offset = state["offset"] + len(rows)
            require(offset <= total and (bool(token) == (offset < total)), "query_result_count_mismatch")
            observed = now()
            records = []
            for row in rows:
                data = export_record(row)
                require(data["publication_date"] is not None and str(start) <= data["publication_date"] < str(end), "query_result_outside_window")
                records.append(envelope(data, data["publication_number"], run, matcher, rules,
                    [job_ref, ref], observed, "https://patents.google.com/patent/" + data["publication_number"]))
            # A row-offset name stays stable even if response page lengths vary.
            body = b"".join(canonical_json(row) + b"\n" for row in rows)
            file_key = f"{prefix}/part-{state['offset']:012d}.jsonl"
            write_checked(store, file_key, body, content_type="application/x-ndjson")
            write_json(store, file_key + ".metadata.json", {"job_id": job_id, "query_plan_key": plan_key,
                "offset": state["offset"], "row_count": len(rows), "sha256": hashlib.sha256(body).hexdigest()})
            state = {**state, "offset": offset, "total": total, "page_token": token}
            if not token:
                job = client.job(job_id, query)
                metadata = {"google_cloud_project": PROJECT, "job_id": job_id, "location": "US", "source_table": "patents-public-data.patents.publications",
                    "query_plan_key": plan_key, "query_plan_hash": digest(plan), "query": query,
                    "provenance": provenance, "statistics": job.get("statistics", {}), "row_count": state["total"],
                    "export_date": state["export_date"], "status": "exported", "coverage": scope["coverage"]}
                write_json(store, prefix + "/export-metadata.json", metadata)
            run.commit_page(records, next_cursor=json.dumps(state, sort_keys=True) if token else None, exhausted=not token)
            pages += 1
            print(json.dumps({"stage": "page_committed", "job_id": job_id, "exported_rows": offset, "total_rows": total}), flush=True)
        require(run.state["record_count"] == state["total"], "query_duplicate_records_or_missing_rows")
        result = outcome(run, "complete")
        return {**result, "job_id": job_id, "export_prefix": prefix, "statistics": job.get("statistics", {})}
    except SourceIssue as exc:
        return outcome(run, "partial" if exc.partial else "failed", exc.code)
    except Exception:
        if not run.closed:
            run.finish("failed", "bigquery_collection_failed")
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--maximum-bytes-billed", type=int, required=True)
    p.add_argument("--page-size", type=int, default=500)
    p.add_argument("--max-pages", type=int, default=100)
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--credentials", type=Path, default=ROOT / "config/google-patents-aws.json")
    p.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    p.add_argument("--universe", type=Path, default=COLLECTION_UNIVERSE)
    p.add_argument("--output", type=Path, default=ROOT / "reports/patent-bigquery-collection.json")
    args = p.parse_args()
    settings = StorageSettings.load(args.storage_config)
    with session(args.credentials) as http:
        result = collect(settings.store(), settings, load_json(args.universe), load_json(ROOT / "config/sectors.v1.json"),
            load_json(args.plan), args.maximum_bytes_billed, BigQuery(http), args.page_size, args.max_pages, args.refresh)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    summary = {k:v for k,v in result.items() if k != "statistics"}
    if "statistics" in result:
        summary["total_bytes_billed"] = result["statistics"].get("query", {}).get("totalBytesBilled")
    print(json.dumps(summary))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())
