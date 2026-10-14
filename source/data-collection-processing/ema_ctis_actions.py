#!/usr/bin/env python3
"""Collect public EMA CTIS submissions, authorizations, and refusals by period.

CTIS does not publish an application while it is still confidential/pending.
Consequently, submission events in this output are submissions that have become
public after a regulatory decision, not a real-time feed of pending applications.
JSON is streamed directly to S3 without creating a local file.

Examples:
    python ema_ctis_actions.py day 2026-08-07
    python ema_ctis_actions.py month 2026-07
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import date, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from clinicaltrials_studies import parse_date, period_bounds


SEARCH_URL = "https://euclinicaltrials.eu/ctis-public-api/search"
RETRIEVE_URL = "https://euclinicaltrials.eu/ctis-public-api/retrieve/{ct_number}"
PORTAL_URL = "https://euclinicaltrials.eu/ctis-public/view/{ct_number}"
S3_PREFIX = "s3://processed-059416028963-us-east-1-an/ema/"
USER_AGENT = "ema-ctis-actions/1.0 (+https://euclinicaltrials.eu/)"
PAGE_SIZE = 100


def request_json(
    url: str,
    payload: dict[str, Any] | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers)
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=90) as response:
                result = json.load(response)
            if not isinstance(result, dict):
                raise RuntimeError("CTIS returned an unexpected response")
            return result
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"CTIS returned HTTP {exc.code}: {detail[:500]}") from exc
        except (URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"could not contact CTIS: {exc}") from exc
            time.sleep(2**attempt)
        except json.JSONDecodeError as exc:
            raise RuntimeError("CTIS returned invalid JSON") from exc
    raise AssertionError("unreachable")


def parse_date_value(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    for pattern in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def discover_candidates(start: date) -> list[dict[str, Any]]:
    """Find decided public records from the requested start through today."""
    candidates: dict[str, dict[str, Any]] = {}
    page = 1
    while True:
        payload = {
            "pagination": {"page": page, "size": PAGE_SIZE},
            "sort": {"property": "decisionDate", "direction": "DESC"},
            "searchCriteria": {},
        }
        response = request_json(SEARCH_URL, payload)
        results = response.get("data", [])
        pagination = response.get("pagination", {})
        if not isinstance(results, list):
            raise RuntimeError("CTIS search response has no valid data list")
        if not results:
            break

        page_dates: list[date] = []
        for result in results:
            if not isinstance(result, dict):
                continue
            decision_date = parse_date_value(result.get("decisionDateOverall"))
            if decision_date is None:
                continue
            page_dates.append(decision_date)
            if decision_date >= start and result.get("ctNumber"):
                candidates[str(result["ctNumber"])] = result

        # Results are sorted newest-first. Applications submitted in the period
        # cannot have a decision before their submission date.
        if page_dates and min(page_dates) < start:
            break
        if not pagination.get("nextPage"):
            break
        page += 1
        if page > 100:
            raise RuntimeError("CTIS candidate search exceeded its 10,000-result public limit")
    return list(candidates.values())


def compact_application(application: dict[str, Any]) -> dict[str, Any]:
    excluded = {"partI", "partIIInfo", "ctMSCsByApplication", "decisions"}
    return {key: value for key, value in application.items() if key not in excluded}


def classify_decision(value: Any) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized.startswith("not_author") or normalized in {"refused", "rejected"}:
        return "REJECTED"
    if "author" in normalized or normalized in {"accepted", "approved"}:
        return "ACCEPTED"
    return None


def collect_actions(start: date, end: date) -> dict[str, Any]:
    candidates = discover_candidates(start)
    submissions: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    trials: list[dict[str, Any]] = []

    for summary in candidates:
        ct_number = str(summary["ctNumber"])
        detail = request_json(RETRIEVE_URL.format(ct_number=ct_number))
        trials.append(detail)
        authorized = detail.get("authorizedApplication", {})
        applications = authorized.get("applicationInfo", []) if isinstance(authorized, dict) else []
        if not isinstance(applications, list):
            continue

        for application in applications:
            if not isinstance(application, dict):
                continue
            application_summary = compact_application(application)
            submission_date = parse_date_value(application.get("submissionDate"))
            if submission_date is not None and start <= submission_date <= end:
                submissions.append(
                    {
                        "action": "SUBMITTED",
                        "actionDate": submission_date.isoformat(),
                        "ctNumber": ct_number,
                        "portalUrl": PORTAL_URL.format(ct_number=ct_number),
                        "publiclyVisibleAfterDecision": True,
                        "application": application_summary,
                        "trialSummary": summary,
                    }
                )

            decisions = application.get("decisions", [])
            if not isinstance(decisions, list):
                continue
            for decision in decisions:
                if not isinstance(decision, dict):
                    continue
                decision_date = parse_date_value(decision.get("decisionDate"))
                action = classify_decision(decision.get("decision"))
                if decision_date is None or action is None or not start <= decision_date <= end:
                    continue
                event = {
                    "action": action,
                    "actionDate": decision_date.isoformat(),
                    "ctNumber": ct_number,
                    "memberState": decision.get("mscName"),
                    "portalUrl": PORTAL_URL.format(ct_number=ct_number),
                    "application": application_summary,
                    "decision": decision,
                    "trialSummary": summary,
                }
                (accepted if action == "ACCEPTED" else rejected).append(event)

    key = lambda item: (item["actionDate"], item["ctNumber"], item.get("memberState") or "")
    submissions.sort(key=key)
    accepted.sort(key=key)
    rejected.sort(key=key)
    trials.sort(key=lambda item: str(item.get("ctNumber", "")))
    return {
        "submissionCount": len(submissions),
        "acceptedCount": len(accepted),
        "rejectedCount": len(rejected),
        "submissions": submissions,
        "accepted": accepted,
        "rejected": rejected,
        "trials": trials,
    }


def upload_to_s3(payload: dict[str, Any], object_name: str) -> str:
    if not object_name or object_name.endswith("/"):
        raise RuntimeError("--s3-key must name a JSON object")
    destination = f"{S3_PREFIX}{object_name.lstrip('/')}"
    try:
        process = subprocess.Popen(
            ["aws", "s3", "cp", "-", destination, "--only-show-errors"],
            stdin=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:
        raise RuntimeError("AWS CLI is not installed or is not on PATH") from exc
    assert process.stdin is not None
    try:
        json.dump(payload, process.stdin, ensure_ascii=False, indent=2)
        process.stdin.write("\n")
        process.stdin.close()
    except BrokenPipeError:
        pass
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"AWS CLI upload failed with exit code {return_code}")
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect public EMA CTIS submissions, acceptances, and rejections."
    )
    parser.add_argument("period", choices=("day", "month"))
    parser.add_argument("date", type=parse_date, help="YYYY-MM-DD (or YYYY-MM for month)")
    parser.add_argument("--s3-key", help="S3 object name (default: ema_ctis_PERIOD_START_END.json)")
    return parser.parse_args()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"historical", "daily"}:
        from regulatory_collection import main as shared_main
        return shared_main('ema', sys.argv[1:])
    args = parse_args()
    start, end = period_bounds(args.period, args.date)
    object_name = args.s3_key or f"ema_ctis_{args.period}_{start}_{end}.json"
    try:
        actions = collect_actions(start, end)
        payload = {
            "agency": "European Medicines Agency",
            "database": "Clinical Trials Information System (CTIS)",
            "period": args.period,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "source": SEARCH_URL,
            "coverageNote": (
                "CTIS submissions become public only after regulatory assessment and a decision; "
                "pending confidential submissions are not available through the public portal."
            ),
            **actions,
        }
        destination = upload_to_s3(payload, object_name)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"Uploaded {actions['submissionCount']:,} public submissions, "
        f"{actions['acceptedCount']:,} acceptances, and {actions['rejectedCount']:,} "
        f"rejections for {start} through {end} to {destination}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
