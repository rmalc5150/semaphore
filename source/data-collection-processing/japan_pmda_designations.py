#!/usr/bin/env python3
"""Collect Japan PMDA/MHLW SAKIGAKE designations from the official PDF list."""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
from datetime import date
from urllib.request import Request, urlopen

from pypdf import PdfReader
from clinicaltrials_studies import parse_date, period_bounds

SOURCE_URL = "https://www.pmda.go.jp/files/000235895.pdf"
S3_PREFIX = "s3://processed-059416028963-us-east-1-an/regulatory-designations/japan/"
USER_AGENT = "pmda-sakigake-designations/1.0"


def japanese_date(value: str) -> date:
    era, year, month, day = re.fullmatch(r"([HRS])(\d+)\.(\d+)\.(\d+)", value).groups()
    base = {"H": 1988, "R": 2018, "S": 1925}[era]
    return date(base + int(year), int(month), int(day))


def fetch_records() -> list[dict[str, str]]:
    request = Request(SOURCE_URL, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=120) as response:
        return parse_pdf(response.read())


def parse_pdf(raw: bytes) -> list[dict[str, str]]:
    reader = PdfReader(io.BytesIO(raw))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    pattern = re.compile(r"(?m)^\s*(\d+)\s+([HRS]\d+\.\d+\.\d+)\s*")
    matches = list(pattern.finditer(text))
    records = []
    for index, match in enumerate(matches):
        block = text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)]
        lines = [re.sub(r"\s+", " ", line).strip() for line in block.splitlines() if line.strip()]
        records.append({"listNumber": match.group(1), "designationDate": japanese_date(match.group(2)).isoformat(),
                        "designationDateNative": match.group(2), "recordText": " ".join(lines)})
    if not records:
        raise RuntimeError("no SAKIGAKE records could be parsed from PMDA PDF")
    return records


def upload(payload: dict, key: str) -> str:
    destination = S3_PREFIX + key.lstrip("/")
    process = subprocess.Popen(["aws", "s3", "cp", "-", destination, "--only-show-errors"],
                               stdin=subprocess.PIPE, text=True, encoding="utf-8")
    assert process.stdin is not None
    json.dump(payload, process.stdin, ensure_ascii=False, indent=2)
    process.stdin.write("\n"); process.stdin.close()
    if process.wait(): raise RuntimeError("AWS CLI upload failed")
    return destination


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"historical", "daily"}:
        from regulatory_collection import main as shared_main
        return shared_main('japan', sys.argv[1:])
    parser = argparse.ArgumentParser(description="Collect Japanese SAKIGAKE designation records.")
    parser.add_argument("period", choices=("day", "month"))
    parser.add_argument("date", type=parse_date, help="YYYY-MM-DD (or YYYY-MM for month)")
    parser.add_argument("--s3-key")
    args = parser.parse_args(); start, end = period_bounds(args.period, args.date)
    try:
        snapshot = fetch_records()
        events = [{"eventDate": r["designationDate"], "regulator": "MHLW/PMDA", "jurisdiction": "Japan",
                   "normalizedCategory": "BREAKTHROUGH", "nativeProgram": "SAKIGAKE",
                   "eventType": "DESIGNATED", "mappingConfidence": "CLOSE_EQUIVALENT", "record": r}
                  for r in snapshot if start <= date.fromisoformat(r["designationDate"]) <= end]
        payload = {"regulator": "MHLW/PMDA", "period": args.period, "startDate": str(start), "endDate": str(end),
                   "source": SOURCE_URL, "coverageNote": "SAKIGAKE is mapped as a close counterpart, not an exact FDA Breakthrough Therapy equivalent.",
                   "eventCount": len(events), "events": events, "snapshot": snapshot}
        key = args.s3_key or f"pmda_designations_{args.period}_{start}_{end}.json"
        destination = upload(payload, key)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr); return 1
    print(f"Uploaded {len(events)} Japanese designation events to {destination}"); return 0


if __name__ == "__main__": raise SystemExit(main())
