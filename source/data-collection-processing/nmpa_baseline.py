#!/usr/bin/env python3
"""Build a checkpointed NMPA registry inventory and fixed-ID detail plan.

The public NMPA listing has no disclosure-date column.  A date-window collector
therefore has to fetch every detail page, and its listing can change during a
multi-day run.  This helper first records the IDs observed on every listing
page.  A completed inventory can then be frozen into deterministic cohorts for
the existing NMPA detail collector.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
from html import unescape
import json
from pathlib import Path
import re
from urllib.parse import urlencode

from collection_storage import (AlreadyComplete, CollectionRun, Conflict,
    StorageSettings, now, task_spec, write_json)
from research_contract import ROOT, digest, load_json, seal_record, validate_record
from regulatory_collection import EvidenceClient, SourceIssue, instant
from regulatory_sources import nmpa_summaries
import nmpa_drug_trials as legacy


VERSION = "nmpa-inventory-1.0"
COVERAGE = (
    "Observed NMPA registration-ID inventory. Listing totals and page membership "
    "may change during collection; completion means every page advertised by the "
    "last response was visited, not that a transactionally frozen snapshot exists."
)


def require(value, code):
    if not value:
        raise SourceIssue(code)


def listing_page(document: str, expected_page: int):
    rows = nmpa_summaries(document)
    require(rows, "nmpa_empty_or_unparseable_page")
    visible = unescape(re.sub(r"<[^>]+>", " ", document))
    current = re.search(r"当前第\s*(\d+)\s*页", visible)
    # Trial descriptions can contain document page counts. Only use the
    # totals immediately following the registry's current-page indicator.
    pagination = re.search(r"当前第\s*\d+\s*页\s*[,，]\s*共\s*(\d+)\s*页"
                           r"\s*[,，]\s*共\s*(\d+)\s*条记录", visible)
    require(current is not None and int(current.group(1)) == expected_page,
            "nmpa_page_parameter_ignored")
    require(pagination is not None, "nmpa_pagination_unverified")
    total_pages, total_records = map(int, pagination.groups())
    require(expected_page <= total_pages, "nmpa_page_out_of_range")
    return rows, total_pages, total_records


def valid_pending_listing(document, expected_page):
    """A rendered 202 is usable only with the exact, fully populated page."""
    try:
        rows, pages, total = listing_page(document, expected_page)
        require(pages == (total + 19) // 20, 'nmpa_inconsistent_pagination')
        require(len(rows) == min(20, total - (expected_page - 1) * 20), 'nmpa_incomplete_listing_page')
        require(len({row['registrationNumber'] for row in rows}) == len(rows), 'nmpa_duplicate_listing_row')
        return True
    except SourceIssue:
        return False


def inventory_record(row, run, evidence, observed_at, page_number,
                     total_pages, total_records):
    return seal_record({
        "document_type": "collected_record", "schema_version": "1.0",
        "source": "nmpa_trials", "dataset": "registry_inventory",
        "source_record_id": row["registrationNumber"],
        "source_record_id_basis": "provider", "source_url": row["detailUrl"],
        "universe_version": run.universe["universe_version"],
        "company_ids": [], "listing_ids": [], "product_ids": [], "person_ids": [],
        "entity_match_status": "unresolved", "event_at": None,
        "available_at": None, "source_updated_at": None,
        "ingested_at": observed_at, "availability_basis": "unknown",
        "availability_evidence": [], "run_id": run.run_id,
        "payload": {
            "registration_number": row["registrationNumber"],
            "title": row.get("title"),
            "search_result_columns": row.get("searchResultColumns", []),
            "detail_url": row["detailUrl"], "listing_page": page_number,
            "advertised_total_pages": total_pages,
            "advertised_total_records": total_records,
            "coverage_note": COVERAGE, "source_evidence": evidence,
        },
    })


def committed_ids(store, manifest):
    output = set()
    for page in manifest["pages"]:
        for batch in page["batches"]:
            stored = store.get(batch["key"])
            if stored is None or hashlib.sha256(stored.body).hexdigest() != batch["sha256"]:
                raise Conflict("missing or corrupt committed inventory batch")
            rows = [json.loads(line) for line in stored.body.splitlines()]
            if len(rows) != batch["records"]:
                raise Conflict("inventory batch count mismatch")
            output.update(row["source_record_id"] for row in rows)
    return output


def inventory(store, settings, universe, taxonomy, snapshot_date, max_pages=None,
              refresh=False, client=None):
    scope = {"coverage": COVERAGE, "listing_page_size": 20,
             "snapshot_date": snapshot_date.isoformat()}
    spec = task_spec("nmpa_trials", "registry_inventory", "daily",
        instant(snapshot_date), instant(snapshot_date + timedelta(days=1)),
        scope, VERSION, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings,
                                  resume=not refresh, refresh=refresh)
    except AlreadyComplete as exc:
        return {"status": "complete", "already_complete": True,
                "manifest": str(exc)}
    client = client or EvidenceClient(store, "nmpa_trials")
    seen = committed_ids(store, run.state)
    page_number = json.loads(run.cursor)["page"] if run.cursor else 1
    attempted = 0
    try:
        while not run.exhausted:
            if max_pages is not None and attempted >= max_pages:
                manifest = run.finish("partial", "page_limit")
                return {"status": "partial", "reason": "page_limit",
                        "manifest": manifest, "records": run.state["record_count"]}
            client.evidence = []
            url = legacy.SEARCH_URL + "?" + urlencode(
                {"keywords": "", "currentpage": page_number})
            document = client.rendered(url, pending_validator=lambda content: valid_pending_listing(content, page_number))
            rows, total_pages, total_records = listing_page(document, page_number)
            page_hash = digest(rows)
            observed_at = now()
            new_rows = []
            for row in rows:
                if row["registrationNumber"] not in seen:
                    new_rows.append(inventory_record(row, run, list(client.evidence),
                        observed_at, page_number, total_pages, total_records))
                    seen.add(row["registrationNumber"])
            sequence = len(run.state["pages"])
            write_json(store, run.state["manifest_prefix"] +
                f"/inputs/{sequence:08d}.json", {
                    "evidence": client.evidence, "listing_page": page_number,
                    "page_hash": page_hash,
                    "provider_ids": [row["registrationNumber"] for row in rows],
                    "new_provider_ids": [row["source_record_id"] for row in new_rows],
                    "advertised_total_pages": total_pages,
                    "advertised_total_records": total_records,
                })
            exhausted = page_number == total_pages
            next_cursor = None if exhausted else json.dumps(
                {"page": page_number + 1}, sort_keys=True)
            run.commit_page(new_rows, next_cursor=next_cursor, exhausted=exhausted)
            attempted += 1
            if exhausted:
                manifest = run.finish("complete", expected_records=run.state["record_count"])
                return {"status": "complete", "manifest": manifest,
                    "records": run.state["record_count"],
                    "advertised_total_pages": total_pages,
                    "advertised_total_records": total_records,
                    "coverage_ratio": (run.state["record_count"] / total_records
                                       if total_records else 1.0)}
            page_number += 1
    except SourceIssue as exc:
        status = "partial" if exc.partial else "failed"
        diagnostics = run.state["manifest_prefix"] + "/failure.json"
        write_json(store, diagnostics, {"reason": exc.code,
            "diagnostics": exc.diagnostics, "evidence": client.evidence,
            "cursor": run.cursor})
        return {"status": status, "reason": exc.code,
            "manifest": run.finish(status, exc.code), "diagnostics": diagnostics}
    except KeyboardInterrupt:
        return {"status": "partial", "reason": "interrupted",
            "manifest": run.finish("partial", "interrupted")}


def read_completed_inventory(store, manifest_key, universe):
    stored = store.get(manifest_key)
    if stored is None:
        raise ValueError("inventory manifest does not exist")
    manifest = json.loads(stored.body)
    if (manifest.get("status") != "complete" or not manifest.get("exhausted") or
            manifest.get("task", {}).get("dataset") != "registry_inventory"):
        raise ValueError("inventory manifest must be complete and exhausted")
    records = []
    evidence = set()
    for page in manifest["pages"]:
        for batch in page["batches"]:
            raw = store.get(batch["key"])
            if raw is None or hashlib.sha256(raw.body).hexdigest() != batch["sha256"]:
                raise ValueError("inventory batch checksum mismatch")
            batch_rows = [json.loads(line) for line in raw.body.splitlines()]
            if len(batch_rows) != batch["records"]:
                raise ValueError("inventory batch count mismatch")
            for record in batch_rows:
                if validate_record(record, universe):
                    raise ValueError("invalid inventory record")
                for ref in record["payload"]["source_evidence"]:
                    pair = (ref["key"], ref["sha256"])
                    if pair not in evidence:
                        source = store.get(ref["key"])
                        if source is None or hashlib.sha256(source.body).hexdigest() != ref["sha256"]:
                            raise ValueError("inventory evidence checksum mismatch")
                        evidence.add(pair)
                records.append(record)
    ids = sorted({record["source_record_id"] for record in records})
    if len(ids) != manifest["record_count"]:
        raise ValueError("inventory contains duplicate registration IDs")
    return stored.body, manifest, ids


def build_plan(store, manifest_key, universe, cohort_size):
    raw, manifest, ids = read_completed_inventory(store, manifest_key, universe)
    cohorts = [ids[offset:offset + cohort_size]
               for offset in range(0, len(ids), cohort_size)]
    plan = {
        "document_type": "nmpa_detail_plan", "schema_version": "1.0",
        "created_at": now(), "inventory_manifest": manifest_key,
        "inventory_manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "inventory_run_id": manifest["run_id"],
        "inventory_records": len(ids), "cohort_size": cohort_size,
        "cohort_count": len(cohorts),
        "cohorts": [{"sequence": number, "registration_ids": cohort,
                     "cohort_hash": digest(cohort)}
                    for number, cohort in enumerate(cohorts)],
        "coverage_note": ("Fixed-ID detail cohorts derived from one completed "
                          "observed NMPA listing inventory."),
    }
    plan_id = digest({key: value for key, value in plan.items() if key != "created_at"})
    key = f"manifests/plans/nmpa_baseline/{plan_id}.json"
    write_json(store, key, plan)
    return key, plan


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-config", type=Path,
                        default=ROOT / "config/collection-storage.s3.json")
    parser.add_argument("--backend", choices=("local", "s3"))
    parser.add_argument("--output-root")
    parser.add_argument("--universe", type=Path,
                        default=ROOT / "config/company-universe.v0.2.json")
    parser.add_argument("--taxonomy", type=Path,
                        default=ROOT / "config/sectors.v1.json")
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect = subparsers.add_parser("inventory")
    collect.add_argument("date", nargs="?", type=date.fromisoformat,
                         default=datetime.now(timezone.utc).date())
    collect.add_argument("--max-pages", type=int)
    collect.add_argument("--refresh", action="store_true")
    plan = subparsers.add_parser("plan")
    plan.add_argument("--manifest-key", required=True)
    plan.add_argument("--cohort-size", type=int, default=200)
    return parser.parse_args()


def main():
    args = parse_args()
    if getattr(args, "max_pages", None) is not None and args.max_pages < 1:
        raise SystemExit("--max-pages must be positive")
    if getattr(args, "cohort_size", 1) < 1 or getattr(args, "cohort_size", 1) > 1000:
        raise SystemExit("--cohort-size must be between 1 and 1000")
    settings = StorageSettings.load(args.storage_config,
        {"backend": args.backend, "local_root": args.output_root})
    store = settings.store()
    universe, taxonomy = load_json(args.universe), load_json(args.taxonomy)
    if args.command == "inventory":
        result = inventory(store, settings, universe, taxonomy, args.date,
                           args.max_pages, args.refresh)
    else:
        key, plan = build_plan(store, args.manifest_key, universe, args.cohort_size)
        result = {"status": "planned", "plan_key": key,
                  "inventory_records": plan["inventory_records"],
                  "cohort_count": plan["cohort_count"]}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if result["status"] in {"complete", "partial", "planned"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
