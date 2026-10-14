#!/usr/bin/env python3
"""Collect FDA drug approvals and public Complete Response Letters by period.

"Rejections" are represented by FDA Complete Response Letters (CRLs): FDA has
completed its review but cannot approve the application in its present form.
The output is streamed directly to S3 and is never written to local disk.

Examples:
    python fda_drug_actions.py day 2026-08-07
    python fda_drug_actions.py month 2026-07
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from clinicaltrials_studies import parse_date, period_bounds


APPROVALS_URL = "https://api.fda.gov/drug/drugsfda.json"
REJECTIONS_URL = "https://api.fda.gov/transparency/crl.json"
S3_PREFIX = "s3://processed-059416028963-us-east-1-an/fda/"
USER_AGENT = "fda-drug-actions/1.0 (+https://open.fda.gov/)"
APPROVAL_PAGE_SIZE = 99
CRL_PAGE_SIZE = 1000

# Optional API credentials are supplied only through the environment or CLI.
OPENFDA_API_KEY = None  # Supply OPENFDA_API_KEY at runtime when needed.


def api_request(
    endpoint: str,
    params: dict[str, str],
    api_key: str | None,
    retries: int = 3,
) -> dict[str, Any]:
    request_params = dict(params)
    if api_key:
        request_params["api_key"] = api_key
    url = f"{endpoint}?{urlencode(request_params)}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise RuntimeError("openFDA returned an unexpected response")
            return payload
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404 and "No matches found" in detail:
                return {"meta": {"results": {"total": 0}}, "results": []}
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"openFDA returned HTTP {exc.code}: {detail[:500]}") from exc
        except (URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"could not contact openFDA: {exc}") from exc
            time.sleep(2**attempt)
        except json.JSONDecodeError as exc:
            raise RuntimeError("openFDA returned invalid JSON") from exc
    raise AssertionError("unreachable")


def result_total(payload: dict[str, Any]) -> int:
    total = payload.get("meta", {}).get("results", {}).get("total", 0)
    return total if isinstance(total, int) else 0


def fetch_approvals(start: date, end: date, api_key: str | None) -> tuple[list[dict[str, Any]], str | None]:
    start_stamp = start.strftime("%Y%m%d")
    end_stamp = end.strftime("%Y%m%d")
    search = f"submissions.submission_status_date:[{start_stamp} TO {end_stamp}]"
    applications: list[dict[str, Any]] = []
    skip = 0
    last_updated: str | None = None

    while True:
        payload = api_request(
            APPROVALS_URL,
            {
                "search": search,
                "limit": str(APPROVAL_PAGE_SIZE),
                "skip": str(skip),
            },
            api_key,
        )
        last_updated = payload.get("meta", {}).get("last_updated") or last_updated
        page = payload.get("results", [])
        if not isinstance(page, list):
            raise RuntimeError("openFDA Drugs@FDA response has no valid results list")
        applications.extend(item for item in page if isinstance(item, dict))
        skip += len(page)
        if not page or skip >= result_total(payload):
            break

    approvals: list[dict[str, Any]] = []
    for application in applications:
        for submission in application.get("submissions", []):
            if not isinstance(submission, dict):
                continue
            action_date = submission.get("submission_status_date", "")
            if submission.get("submission_status") != "AP" or not (
                start_stamp <= action_date <= end_stamp
            ):
                continue
            approvals.append(
                {
                    "action": "APPROVAL",
                    "actionDate": datetime.strptime(action_date, "%Y%m%d").date().isoformat(),
                    "applicationNumber": application.get("application_number"),
                    "sponsorName": application.get("sponsor_name"),
                    "submission": submission,
                    "products": application.get("products", []),
                    "openfda": application.get("openfda", {}),
                }
            )
    approvals.sort(key=lambda item: (item["actionDate"], item.get("applicationNumber") or ""))
    return approvals, last_updated


def parse_crl_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError:
        return None


def fetch_rejections(start: date, end: date, api_key: str | None) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch all published CRLs, then date-filter because their dates are MM/DD/YYYY strings."""
    records: list[dict[str, Any]] = []
    skip = 0
    last_updated: str | None = None
    while True:
        payload = api_request(
            REJECTIONS_URL,
            {"limit": str(CRL_PAGE_SIZE), "skip": str(skip)},
            api_key,
        )
        last_updated = payload.get("meta", {}).get("last_updated") or last_updated
        page = payload.get("results", [])
        if not isinstance(page, list):
            raise RuntimeError("openFDA CRL response has no valid results list")
        records.extend(item for item in page if isinstance(item, dict))
        skip += len(page)
        if not page or skip >= result_total(payload):
            break

    rejections: list[dict[str, Any]] = []
    for record in records:
        letter_date = parse_crl_date(record.get("letter_date"))
        if str(record.get("letter_type", "")).upper() != "COMPLETE RESPONSE":
            continue
        if letter_date is None or not start <= letter_date <= end:
            continue
        output = dict(record)
        output["action"] = "COMPLETE_RESPONSE"
        output["actionDate"] = letter_date.isoformat()
        rejections.append(output)
    rejections.sort(key=lambda item: (item["actionDate"], item.get("application_number") or ""))
    return rejections, last_updated


def upload_to_s3(payload: dict[str, Any], object_name: str) -> str:
    import subprocess

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
        description="Collect FDA drug approvals and public Complete Response Letters."
    )
    parser.add_argument("period", choices=("day", "month"))
    parser.add_argument("date", type=parse_date, help="YYYY-MM-DD (or YYYY-MM for month)")
    parser.add_argument("--s3-key", help="S3 object name (default: fda_actions_PERIOD_START_END.json)")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENFDA_API_KEY"),
        help="openFDA API key (or set OPENFDA_API_KEY); optional",
    )
    return parser.parse_args()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"historical", "daily"}:
        from regulatory_collection import main as shared_main
        return shared_main('fda', sys.argv[1:])
    args = parse_args()
    start, end = period_bounds(args.period, args.date)
    object_name = args.s3_key or f"fda_actions_{args.period}_{start}_{end}.json"
    try:
        approvals, approvals_updated = fetch_approvals(start, end, args.api_key)
        rejections, rejections_updated = fetch_rejections(start, end, args.api_key)
        payload = {
            "agency": "U.S. Food and Drug Administration",
            "period": args.period,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "sources": {
                "approvals": APPROVALS_URL,
                "completeResponseLetters": REJECTIONS_URL,
            },
            "sourceLastUpdated": {
                "approvals": approvals_updated,
                "completeResponseLetters": rejections_updated,
            },
            "approvalCount": len(approvals),
            "rejectionCount": len(rejections),
            "approvals": approvals,
            "rejections": rejections,
        }
        destination = upload_to_s3(payload, object_name)
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"Uploaded {len(approvals):,} approvals and {len(rejections):,} public CRLs "
        f"for {start} through {end} to {destination}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
