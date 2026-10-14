#!/usr/bin/env python3
"""Create idempotent patent events by comparing successive public snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


GRANT_KIND_PREFIXES = ("B", "C", "E")


def record_key(record: dict[str, Any]) -> str:
    return str(record.get("publication_number") or record.get("application_number") or "")


def is_grant(record: dict[str, Any]) -> bool:
    kind = str(record.get("kind_code") or record.get("publication_number") or "").rsplit("-", 1)[-1]
    return bool(record.get("grant_date")) or kind.startswith(GRANT_KIND_PREFIXES)


def event_id(event_type: str, record: dict[str, Any], event_date: str, value: Any = None) -> str:
    identity = "|".join((event_type, record_key(record), event_date, json.dumps(value, sort_keys=True)))
    return hashlib.sha256(identity.encode()).hexdigest()


def make_event(
    event_type: str,
    record: dict[str, Any],
    event_date: str,
    detected_at: str,
    source: str,
    changes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "eventId": event_id(event_type, record, event_date, changes),
        "eventType": event_type,
        "eventDate": event_date,
        "detectedAt": detected_at,
        "source": source,
        "company": {
            "name": record.get("matched_company"),
            "sector": record.get("company_sector"),
        },
        "patent": {
            "publicationNumber": record.get("publication_number"),
            "applicationNumber": record.get("application_number"),
            "familyId": record.get("family_id"),
            "title": record.get("title"),
            "filingDate": record.get("filing_date"),
            "priorityDate": record.get("priority_date"),
            "grantDate": record.get("grant_date"),
            "status": record.get("status"),
            "assignees": record.get("assignees", []),
            "cpcCodes": record.get("cpc_codes", []),
        },
        "technologyClassifications": record.get("technology_classifications", []),
    }
    if changes:
        event["changes"] = changes
    return event


def changed(previous: dict[str, Any], current: dict[str, Any], field: str) -> dict[str, Any] | None:
    before, after = previous.get(field), current.get(field)
    if before == after or after in (None, "", []):
        return None
    return {"field": field, "previous": before, "current": after}


def create_events(
    previous_records: Iterable[dict[str, Any]],
    current_records: Iterable[dict[str, Any]],
    run_date: date,
    source: str = "google-patents-public-data",
    detected_at: str | None = None,
) -> list[dict[str, Any]]:
    detected_at = detected_at or datetime.now(timezone.utc).isoformat()
    previous = {record_key(row): row for row in previous_records if record_key(row)}
    events: list[dict[str, Any]] = []
    for record in current_records:
        key = record_key(record)
        if not key:
            continue
        old = previous.get(key)
        if old is None:
            published = str(record.get("publication_date") or run_date.isoformat())
            event_type = "PATENT_GRANT_PUBLISHED" if is_grant(record) else "PATENT_APPLICATION_PUBLISHED"
            events.append(make_event(event_type, record, published, detected_at, source))
            continue
        status_change = changed(old, record, "status")
        if status_change:
            status_date = str(record.get("status_date") or run_date.isoformat())
            events.append(make_event("PATENT_STATUS_CHANGED", record, status_date, detected_at, source, status_change))
        if not is_grant(old) and is_grant(record):
            grant_date = str(record.get("grant_date") or run_date.isoformat())
            events.append(make_event("PATENT_GRANTED", record, grant_date, detected_at, source))
        assignment_change = changed(old, record, "assignees")
        if assignment_change:
            assignment_date = str(record.get("assignment_date") or run_date.isoformat())
            events.append(make_event("PATENT_ASSIGNEE_CHANGED", record, assignment_date, detected_at, source, assignment_change))
    return sorted(events, key=lambda row: (row["eventDate"], row["eventType"], row["eventId"]))


def read_jsonl(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current", help="current normalized patent snapshot (JSONL)")
    parser.add_argument("--previous", help="previous normalized patent snapshot (JSONL); omit for bootstrap")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--source", default="google-patents-public-data")
    parser.add_argument("--output", required=True)
    parser.add_argument("--emit-bootstrap-events", action="store_true", help="emit all current rows when no prior state exists")
    args = parser.parse_args()
    current = read_jsonl(args.current)
    previous = read_jsonl(args.previous)
    events = create_events(previous, current, args.date, args.source)
    if not args.previous and not args.emit_bootstrap_events:
        events = []
    payload = {
        "schemaVersion": "1.0",
        "collector": "patent-events",
        "runDate": args.date.isoformat(),
        "source": args.source,
        "eventCount": len(events),
        "events": events,
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"events": len(events), "output": args.output}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
