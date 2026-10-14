#!/usr/bin/env python3
"""Evidence-backed archive checks without company, sector or language filters."""
import argparse
from datetime import date, datetime, timezone
import fcntl
import json
from pathlib import Path

from collection_storage import StorageSettings, now, write_json
from news_collection import NewsClient, article_time, page_info
from regulatory_collection import require
from research_contract import ROOT, canonical_json, digest, load_json


def probe(client, start, end, extra=None):
    params = {"published_after": start.isoformat() + "T00:00:00",
        "published_before": end.isoformat() + "T00:00:00",
        "sort": "published_at", "group_similar": "false", "limit": 3, "page": 1,
        **(extra or {})}
    data = client.page(params)
    rows, _, total, exhausted = page_info("marketaux", data, 1, 3)
    stamps = [article_time("marketaux", row) for row in rows]
    require(all(start <= t.date() < end for t in stamps), "archive_probe_date_filter_not_respected")
    return {"start": str(start), "end_exclusive": str(end), "parameters": params,
        "found": total, "returned": len(rows), "sample_exhausts_query": exhausted,
        "sample": [{"uuid": r["uuid"], "published_at": t.isoformat(), "url": r["url"]} for r, t in zip(rows, stamps)],
        "evidence": list(client.evidence), "status": "historical_articles_returned" if rows else "empty_query_not_proof_of_absence"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, action="append")
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--search")
    parser.add_argument("--published-on", type=date.fromisoformat)
    parser.add_argument("--max-requests", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    today = datetime.now(timezone.utc).date()
    require(bool(args.year) != bool(args.start or args.end), "Choose years or an explicit start/end")
    windows = [(date(y, 1, 1), min(date(y + 1, 1, 1), today)) for y in sorted(set(args.year or []))]
    if not args.year:
        windows = [(args.start, args.end)]
    require(all(left and right and left < right <= today for left, right in windows), "invalid_archive_windows")
    config = load_json(ROOT / "config/news-collection.json")
    with (ROOT / ".news-collection.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        import boto3
        secret = boto3.client("secretsmanager", region_name=config["region"]).get_secret_value(SecretId=config["secret_id"])
        key = json.loads(secret["SecretString"])[config["providers"]["marketaux"]["secret_field"]]
        settings = StorageSettings.load(ROOT / config["storage_config"])
        store = settings.store()
        client = NewsClient(store, "marketaux", key, config["providers"]["marketaux"]["max_requests_per_day"], args.max_requests)
        results = []
        for start, end in windows:
            try:
                extra = {**({"search": args.search} if args.search else {}),
                         **({"published_on": str(args.published_on)} if args.published_on else {})}
                result = probe(client, start, end, extra)
            except Exception as exc:
                result = {"start": str(start), "end_exclusive": str(end), "status": "failed",
                    "reason": getattr(exc, "code", "probe_exception"), "error_type": type(exc).__name__}
            results.append(result)
            # Keep full source URLs only in the evidence report, not console output.
            print(json.dumps({k: v for k, v in result.items() if k not in {"sample", "evidence", "parameters"}}), flush=True)
            if result["status"] == "failed":
                break
        report = {"checked_at": now(), "provider": "marketaux", "plan": "Standard",
            "scope": "unfiltered_archive" if not args.search else "search_archive", "results": results,
            "requested_windows": len(windows), "full_archive_coverage_established": False}
        report["evidence_report_key"] = "operations/news/history_probes/" + digest(report) + ".json"
        write_json(store, report["evidence_report_key"], report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(report) + b"\n")
        print(json.dumps({"report": str(args.output), "s3_key": report["evidence_report_key"]}), flush=True)
        return 1 if any(r["status"] == "failed" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
