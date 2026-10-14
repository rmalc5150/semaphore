#!/usr/bin/env python3
"""Verify federated BigQuery access and estimate patent queries without executing them."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from research_contract import ROOT, digest, load_json

PROJECT = "patent-research-508613"
API = "https://bigquery.googleapis.com/bigquery/v2"
TABLE = "patents-public-data.patents.publications"
REQUIRED_FIELDS = {"publication_number", "application_number", "family_id", "country_code", "kind_code",
                   "filing_date", "priority_date", "publication_date", "title_localized", "cpc", "assignee_harmonized"}


def session(credentials_path):
    from google.auth.aws import Credentials
    from google.auth.transport.requests import AuthorizedSession
    credentials = Credentials.from_file(str(credentials_path), scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return AuthorizedSession(credentials)


def response_json(response):
    value = response.json()
    if not response.ok or value.get("error"):
        error = value.get("error", {})
        # Only provider API errors; never print authorization headers or tokens.
        raise RuntimeError(json.dumps({"http_status": response.status_code,
            "reason": error.get("status"), "message": error.get("message", "BigQuery request failed")}))
    return value


def dry_configuration(plan):
    config = deepcopy(plan["configuration"])
    if config.get("dryRun") is not True or set(config) != {"dryRun", "query"}:
        raise ValueError("Only a dry-run query configuration is accepted")
    query = config["query"]
    if query.get("useLegacySql") is not False or not query.get("query"):
        raise ValueError("Require a Standard SQL query")
    ceiling = int(query.pop("maximumBytesBilled"))
    if ceiling <= 0:
        raise ValueError("Require a positive execution ceiling")
    # Estimation cannot execute/bill a query. Remove the execution ceiling here
    # so the estimate remains available when the prepared ceiling is too small.
    # The original plan, including its execution ceiling, is unchanged.
    return config, ceiling


def verify(http, plan):
    table = response_json(http.get(API + "/projects/patents-public-data/datasets/patents/tables/publications", timeout=60))
    dataset = response_json(http.get(API + "/projects/patents-public-data/datasets/patents", timeout=60))
    fields = {f["name"] for f in table["schema"]["fields"]}
    missing = REQUIRED_FIELDS - fields
    if missing:
        raise ValueError("Patent source schema missing fields: " + ", ".join(sorted(missing)))
    config, ceiling = dry_configuration(plan)
    payload = {"configuration": config, "jobReference": {"projectId": PROJECT, "location": dataset["location"]}}
    job = response_json(http.post(API + f"/projects/{PROJECT}/jobs", json=payload, timeout=120))
    if job.get("status", {}).get("errorResult"):
        raise RuntimeError(json.dumps(job["status"]["errorResult"]))
    stats = job.get("statistics", {})
    query_stats = stats.get("query", {})
    size = query_stats.get("totalBytesProcessed", stats.get("totalBytesProcessed"))
    if size is None:
        raise ValueError("Dry run did not return a scan estimate")
    size = int(size)
    report = {"status": "access_and_dry_run_verified", "checked_at": datetime.now(timezone.utc).isoformat(),
        "project_id": PROJECT, "project_number": "24037405713", "source_table": TABLE,
        "location": dataset["location"], "authentication": "aws_workload_identity_federation",
        "source_metadata": {k: table.get(k) for k in ("id", "etag", "lastModifiedTime", "numRows", "numBytes", "timePartitioning", "rangePartitioning", "clustering")},
        "query_plan_hash": digest(plan), "provenance": plan.get("provenance"),
        "estimated_bytes_processed": size, "estimated_tib_processed": size / 1024 ** 4,
        "estimate_accuracy": query_stats.get("totalBytesProcessedAccuracy"),
        "configured_maximum_bytes_billed": ceiling, "estimate_within_ceiling": size <= ceiling,
        "dry_run": True, "data_query_executed": False,
        "freshness_note": "Table modification time is not proof of worldwide publication coverage or freshness."}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", type=Path, default=ROOT / "config/google-patents-aws.json")
    parser.add_argument("--plan", type=Path, default=ROOT / "reports/patent-bigquery-dry-run.json")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/patent-bigquery-access.json")
    args = parser.parse_args()
    with session(args.credentials) as http:
        result = verify(http, load_json(args.plan))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
