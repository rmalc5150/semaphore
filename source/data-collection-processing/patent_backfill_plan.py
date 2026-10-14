#!/usr/bin/env python3
"""Prepare an explicit monthly global patent backfill plan; no external actions."""
import argparse
from datetime import date
import json
from pathlib import Path

from patent_source_coverage import revision
from research_contract import digest, load_json


def plan(coverage, estimate, start, end):
    if start >= end or end > date.fromisoformat(coverage["plan"]["provenance"]["as_of"]):
        raise ValueError("require nonempty range of completed days through coverage as-of date")
    if coverage["status"] != "complete" or not estimate["dry_run"] or not estimate["estimate_within_ceiling"]:
        raise ValueError("require complete coverage and successful bounded dry-run")
    if revision(estimate["source_metadata"]) != coverage["source_revision_after"]:
        raise ValueError("coverage and extraction estimate use different source revisions")
    windows, cursor = [], start
    while cursor < end:
        following = min(date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1), end)
        windows.append({"start": str(cursor), "end_exclusive": str(following),
            "status": "not_started"})
        cursor = following
    byte_ceiling = estimate["configured_maximum_bytes_billed"]
    rate = 6.25  # US on-demand USD/TiB, verified 2026-09-23; excludes free tier.
    return {"status": "proposed_not_scheduled", "date_basis": "publication_date",
        "start": str(start), "end_exclusive": str(end), "window_count": len(windows),
        "windows": windows, "coverage_id": coverage["coverage_id"],
        "coverage_report_hash": digest(coverage), "extraction_estimate_hash": digest(estimate),
        "universe_hash": estimate["provenance"]["universe_hash"],
        "classification_hash": estimate["provenance"]["classification_hash"],
        "source_revision": coverage["source_revision_after"],
        "maximum_bytes_billed_per_query": byte_ceiling,
        "initial_queries_reserved_bytes": len(windows) * byte_ceiling,
        "initial_queries_reserved_usd_before_free_usage": round(len(windows) * byte_ceiling / 1024 ** 4 * rate, 2),
        "pricing_source": "https://cloud.google.com/bigquery/pricing",
        "cost_note": "Planning reservation for one capped query per window, not a billing-account cap. Fresh dry-run required for every window. Excludes retries requiring replacement jobs, refreshes, S3, EC2 and transfer charges.",
        "execution_policy": {"max_active_query_jobs": 1,
            "finish_download_before_next_query": True, "fresh_dry_run_before_each_query": True,
            "temporary_result_expiry": "Stop for review; never automatically rebill or advance an incomplete window.",
            "resume": "Reuse fixed job ID and committed S3 pages.",
            "revision_change": "Record source revision per job and revalidate cost; do not claim all months are one immutable source snapshot.",
            "late_corrections": "New source revisions can change older months; recent-date refresh alone cannot guarantee historical reconciliation."},
        "coverage_gaps": {"source_wide_missing_or_invalid_publication_dates": sum(r["missing_or_invalid_dates"] for r in coverage["countries"]),
            "source_wide_future_dates": sum(r["future_dates"] for r in coverage["countries"]),
            "counts_are_sector_filtered": False,
            "undated_records": "Excluded by date-filtered query; require a separately labeled undated discovery cohort.",
            "country_completeness": "Observed maximum dates are not completeness watermarks.",
            "sector_selection": estimate["provenance"]["coverage_gaps"],
            "athena": "Collect to S3, then review and publish an explicit curated release."}}


def main():
    from historical_policy import historical_start
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--estimate", type=Path, required=True)
    parser.add_argument("--start", type=date.fromisoformat, default=historical_start(), help="default: shared historical start")
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = plan(load_json(args.coverage), load_json(args.estimate), args.start, args.end)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "start", "end_exclusive", "window_count", "initial_queries_reserved_usd_before_free_usage")}))


if __name__ == "__main__":
    main()
