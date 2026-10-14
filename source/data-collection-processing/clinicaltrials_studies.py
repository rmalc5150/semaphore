#!/usr/bin/env python3
"""Fetch ClinicalTrials.gov studies updated during a calendar period.

Examples:
    python clinicaltrials_studies.py day 2026-08-07
    python clinicaltrials_studies.py week 2026-08-03
    python clinicaltrials_studies.py month 2026-07 --s3-key july-studies.json

Weeks run from Monday through Sunday.  The supplied date may be any date in the
requested week or month.  Month dates may be written as YYYY-MM or YYYY-MM-DD.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import date, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://clinicaltrials.gov/api/v2/studies"
S3_PREFIX = "s3://processed-059416028963-us-east-1-an/clinical-trials/"
USER_AGENT = "clinicaltrials-period-fetcher/1.0"
PAGE_SIZE = 1000


def parse_date(value: str) -> date:
    """Parse YYYY-MM-DD, or YYYY-MM as the first day of that month."""
    try:
        if len(value) == 7:
            return date.fromisoformat(f"{value}-01")
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid date {value!r}; use YYYY-MM-DD (or YYYY-MM for a month)"
        ) from exc


def period_bounds(period: str, selected: date) -> tuple[date, date]:
    if period == "day":
        return selected, selected
    if period == "week":
        start = selected - timedelta(days=selected.weekday())
        return start, start + timedelta(days=6)

    start = selected.replace(day=1)
    if start.month == 12:
        following = start.replace(year=start.year + 1, month=1)
    else:
        following = start.replace(month=start.month + 1)
    return start, following - timedelta(days=1)


def request_page(params: dict[str, str], retries: int = 3) -> dict[str, Any]:
    url = f"{API_URL}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise RuntimeError("ClinicalTrials.gov returned an unexpected response")
            return payload
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"ClinicalTrials.gov returned HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except (URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"could not contact ClinicalTrials.gov: {exc}") from exc
            time.sleep(2**attempt)
        except json.JSONDecodeError as exc:
            raise RuntimeError("ClinicalTrials.gov returned invalid JSON") from exc
    raise AssertionError("unreachable")


def fetch_studies(start: date, end: date) -> tuple[list[dict[str, Any]], int | None]:
    query = f"AREA[LastUpdatePostDate]RANGE[{start.isoformat()}, {end.isoformat()}]"
    params = {
        "format": "json",
        "query.term": query,
        "pageSize": str(PAGE_SIZE),
        "countTotal": "true",
    }
    studies: list[dict[str, Any]] = []
    total_count: int | None = None

    while True:
        payload = request_page(params)
        page = payload.get("studies", [])
        if not isinstance(page, list):
            raise RuntimeError("ClinicalTrials.gov response has no valid studies list")
        studies.extend(page)

        if total_count is None and isinstance(payload.get("totalCount"), int):
            total_count = payload["totalCount"]
        token = payload.get("nextPageToken")
        if not token:
            break
        params["pageToken"] = str(token)

    return studies, total_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch studies updated on a calendar day, week, or month."
    )
    parser.add_argument("period", choices=("day", "week", "month"))
    parser.add_argument(
        "date",
        type=parse_date,
        help="date in the period (YYYY-MM-DD; YYYY-MM is also accepted for month)",
    )
    parser.add_argument(
        "--s3-key",
        help="S3 object filename (default: clinicaltrials_PERIOD_START_END.json)",
    )
    return parser.parse_args()


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


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"historical", "daily"}:
        from regulatory_collection import main as shared_main
        return shared_main('clinicaltrials', sys.argv[1:])
    args = parse_args()
    start, end = period_bounds(args.period, args.date)
    object_name = args.s3_key or (
        f"clinicaltrials_{args.period}_{start.isoformat()}_{end.isoformat()}.json"
    )

    try:
        studies, reported_total = fetch_studies(start, end)
        result = {
            "period": args.period,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "studyCount": len(studies),
            "studies": studies,
        }
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if reported_total is not None and reported_total != len(studies):
        print(
            f"warning: API reported {reported_total:,} studies but returned {len(studies):,}",
            file=sys.stderr,
        )
    try:
        destination = upload_to_s3(result, object_name)
    except RuntimeError as exc:
        print(f"error: S3 upload failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Uploaded {len(studies):,} studies updated {start} through {end} to {destination}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
