#!/usr/bin/env python3
"""Join verified USPTO histories to a reviewed patent entity cohort by application."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from collection_storage import StorageSettings, write_checked
from patent_entity_review import checked_body, name_key, put_local
from regulatory_athena import read_inputs
from research_contract import ROOT, canonical_json, digest, load_json

VERSION = "patent-assignment-review-1.0"


def entity_index(rows):
    index = defaultdict(set)
    for row in rows:
        if not row["selected_lei"]:
            continue
        candidate = next(c for c in row["candidates"] if c["lei"] == row["selected_lei"])
        # Only names actually supported by the registry review are eligible.
        for name in [row["reported_name"]] + [m["name"] for m in candidate["matched_names"]]:
            index[name_key(name)].add(row["registry_entity_id"])
    return index


def compare(cohort_row, record, index):
    history = record["payload"]["data"]["assignment_history"]
    latest = history["latest_recorded_assignment_events"]
    names = sorted({a["assigneeNameText"] for e in latest for a in e["assignees"] if a.get("assigneeNameText")})
    recipients = [{"reported_name": name, "registry_entity_ids": sorted(index.get(name_key(name), set()))} for name in names]
    expected = set(cohort_row["registry_entity_ids"])
    if not latest:
        status = "no_dated_assignment_in_response"
    elif not names or any(not event.get("assignees") for event in latest):
        status = "latest_assignment_recipient_missing"
    elif len(latest) > 1:
        status = "multiple_latest_assignment_events_review"
    elif all(len(r["registry_entity_ids"]) == 1 for r in recipients) and {
            r["registry_entity_ids"][0] for r in recipients} == expected:
        status = "reported_recipient_matches_registry_entity"
    else:
        status = "recipient_identity_or_difference_review"
    return {**cohort_row, "comparison_status": status, "observation_id": record["observation_id"],
        "source_url": record["source_url"], "source_evidence": record["payload"]["source_evidence"],
        "source_payload_hash": record["payload_hash"], "assignment_event_count": len(history["events"]),
        "latest_recorded_recipients": recipients, "assignment_history": history,
        "current_ownership_status": "not_established", "point_in_time_eligible": False}


def prepare(store, manifests, entity_root, output_root):
    entity_root = Path(entity_root)
    entity_report = load_json(entity_root / "review.json")
    entities = [json.loads(line) for line in checked_body(entity_root / "entities.jsonl",
        entity_report["files"]["entities.jsonl"]).splitlines()]
    cohort = json.loads(checked_body(entity_root / "assignment-cohort.json", entity_report["files"]["assignment-cohort.json"]))
    numbers = {r["application_number"] for r in cohort}
    if len(numbers) != len(cohort):
        raise ValueError("Duplicate applications in reviewed cohort")
    entries, universe, inputs = read_inputs(store, manifests, allowed={"uspto_odp"}, dataset="patent_assignment_records")
    if digest(universe) != entity_report["universe_hash"]:
        raise ValueError("Assignment and entity-review universe mismatch")
    records = {}
    for entry in entries.values():
        record = entry["record"]
        number = record["source_record_id"]
        if number in records:
            raise ValueError("Multiple observations for an application; select one cohort snapshot explicitly")
        records[number] = record
    if set(records) != numbers:
        raise ValueError("Assignment records do not exactly cover reviewed cohort")
    index = entity_index(entities)
    rows = [compare(c, records[c["application_number"]], index) for c in cohort]
    release_id = digest({"version": VERSION, "entity_release": entity_report["release_id"], "inputs": inputs})
    root = Path(output_root) / release_id
    root.mkdir(parents=True, exist_ok=True)
    files = {"applications.jsonl": put_local(root, "applications.jsonl", b"".join(canonical_json(r) + b"\n" for r in rows))}
    report = {"version": VERSION, "release_id": release_id, "entity_review_release_id": entity_report["release_id"],
        "inputs": inputs, "applications": len(rows), "assignment_events": sum(r["assignment_event_count"] for r in rows),
        "comparison_status_counts": dict(Counter(r["comparison_status"] for r in rows)),
        "current_ownership_verified_records": 0, "point_in_time_eligible_records": 0,
        "athena_status": "not_published", "files": files}
    put_local(root, "review.json", canonical_json(report) + b"\n")
    return root, report


def publish(root, store):
    report = load_json(root / "review.json")
    prefix = "curated/patent_assignment_review/" + report["release_id"]
    for name, meta in report["files"].items():
        write_checked(store, prefix + "/" + name, checked_body(root / name, meta), content_type="application/x-ndjson")
    write_checked(store, prefix + "/review.json", (root / "review.json").read_bytes())
    return prefix


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", action="append", required=True)
    p.add_argument("--entity-root", type=Path, required=True)
    p.add_argument("--output-root", type=Path, default=ROOT / "patent-assignment-review-build")
    p.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    p.add_argument("--publish", action="store_true")
    args = p.parse_args()
    store = StorageSettings.load(args.storage_config).store()
    root, report = prepare(store, args.manifest, args.entity_root, args.output_root)
    if args.publish:
        report = {**report, "s3_prefix": publish(root, store)}
    print(json.dumps({"directory": str(root), **report}))


if __name__ == "__main__":
    main()
