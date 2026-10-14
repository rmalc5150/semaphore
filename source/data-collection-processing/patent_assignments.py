#!/usr/bin/env python3
"""Collect official US assignment histories for explicit, reviewable application cohorts."""
import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec
from patent_adjudication import POLICY_PATH, Reviewer
from patent_collection import ODPClient, SourceIssue, day, envelope, odp_record, outcome, require, RULES_PATH
from regulatory_collection import instant
from research_contract import COLLECTION_UNIVERSE, ROOT, load_json, seal_record
from uspto_patents import application_number


def assignment_kind(text):
    text = (text or "").upper()
    if "RELEASE" in text:
        return "release"
    if "SECURITY" in text or "MORTGAGE" in text:
        return "security_interest"
    if "NAME" in text and "CHANGE" in text:
        return "name_change"
    if "MERGER" in text:
        return "merger"
    if "ASSIGNMENT" in text:
        return "assignment"
    return "other"


def normalize_history(row, reviewer):
    history = []
    for event in row.get("assignmentBag", []):
        names = [a["assigneeNameText"] for a in event.get("assigneeBag", []) if a.get("assigneeNameText")]
        recorded = day(event.get("assignmentRecordedDate"))
        history.append({"reel_frame": event.get("reelAndFrameNumber"),
            "recorded_date": recorded, "received_date": day(event.get("assignmentReceivedDate")),
            "conveyance": event.get("conveyanceText"), "event_kind": assignment_kind(event.get("conveyanceText")),
            "document_url": event.get("assignmentDocumentLocationURI"),
            "assignees": event.get("assigneeBag", []),
            "assignors": [{"name": a.get("assignorName"), "execution_date": day(a.get("executionDate"))} for a in event.get("assignorBag", [])],
            "reported_recipient_links": [reviewer.party(name, "assignment_recipient", recorded) for name in names]})
    history.sort(key=lambda e: (e["recorded_date"] or "", e["reel_frame"] or ""))
    transfers = [e for e in history if e["event_kind"] == "assignment" and e["recorded_date"]]
    latest = max((e["recorded_date"] for e in transfers), default=None)
    # Tied dates remain a set, never an arbitrary winner. Recorded events are
    # not proof that the search found a complete chain or that title is valid.
    return {"events": history, "latest_recorded_assignment_events": [e for e in transfers if e["recorded_date"] == latest],
        "current_ownership_status": "not_established", "chain_completeness": "not_established",
        "recordation_limitation": "https://www.uspto.gov/web/offices/pac/mpep/s301.html"}


def collect(store, settings, universe, taxonomy, numbers, observed_day, client=None, max_records=20):
    numbers = sorted({application_number(n) for n in numbers})
    require(bool(numbers) and max_records > 0, "invalid_cohort")
    scope = {"application_numbers": numbers, "date_basis": "observation_day", "coverage": "Explicit US application cohort only"}
    spec = task_spec("uspto_odp", "patent_assignment_records", "daily", instant(observed_day),
        instant(observed_day + timedelta(days=1)), scope, "patent-assignments-1.0", universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
    except AlreadyComplete as exc:
        return {"status":"complete", "already_complete":True, "manifest":str(exc)}
    client = client or ODPClient(store)
    reviewer = Reviewer(universe, load_json(POLICY_PATH))
    rules = load_json(RULES_PATH)
    offset, count = int(run.cursor or 0), 0
    try:
        while not run.exhausted:
            if count >= max_records:
                return outcome(run, "partial", "record_limit")
            number = numbers[offset]
            client.evidence = []
            response = client.application(number)
            rows = response.get("patentFileWrapperDataBag", [])
            require(response.get("count") == 1 and len(rows) == 1 and rows[0].get("applicationNumberText") == number,
                    "assignment_application_mismatch")
            data = odp_record(rows[0])
            data["assignment_history"] = normalize_history(rows[0], reviewer)
            record = envelope(data, number, run, reviewer.matcher, rules, client.evidence, now(),
                f"https://data.uspto.gov/patent-file-wrapper/search/details/{number}/application-data")
            record["dataset"] = spec["dataset"]
            record["payload"]["record_type"] = "patent_assignment_history"
            record = seal_record(record)
            offset += 1
            run.commit_page([record], next_cursor=str(offset) if offset < len(numbers) else None, exhausted=offset == len(numbers))
            count += 1
        return outcome(run, "complete")
    except SourceIssue as exc:
        return outcome(run, "partial" if exc.partial else "failed", exc.code)
    except Exception:
        if not run.closed:
            run.finish("failed", "assignment_collection_failed")
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    cohort = p.add_mutually_exclusive_group(required=True)
    cohort.add_argument("--applications", nargs="+", type=application_number)
    cohort.add_argument("--cohort-file", type=Path, help="Reviewed JSON array containing application_number")
    p.add_argument("--observed-day", type=date.fromisoformat, required=True)
    p.add_argument("--max-records", type=int, default=20)
    p.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    p.add_argument("--output", type=Path, default=ROOT / "reports/patent-assignment-cohort.json")
    args = p.parse_args()
    numbers = args.applications if args.applications is not None else [
        application_number(r["application_number"]) for r in load_json(args.cohort_file)]
    settings = StorageSettings.load(args.storage_config)
    result = collect(settings.store(), settings, load_json(COLLECTION_UNIVERSE), load_json(ROOT / "config/sectors.v1.json"),
        numbers, args.observed_day, max_records=args.max_records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())
