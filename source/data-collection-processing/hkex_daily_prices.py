#!/usr/bin/env python3
"""Download HKEX daily quotation prices and write them as CSV.

The source is HKEX's official Main Board and GEM daily quotation sheets.  With no
date argument, the newest sheet found within the last seven Hong Kong calendar
days is used, which accounts for weekends and most market holidays.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from hkex_csv_cleaner import filter_by_code, load_excluded_codes
from hkex_cross_listed_prices import enrich_rows, enrichment_columns
from decodo_scraping_api import scrape_url


BASE_URL = "https://www.hkex.com.hk/eng/stat/smstat"
S3_PREFIX = "s3://processed-059416028963-us-east-1-an/hkex/"
USER_AGENT = "hkex-daily-prices/1.0 (+https://www.hkex.com.hk/)"
NUMBER = r"(?:-|N/A|[0-9][0-9,.]*)"


@dataclass(frozen=True)
class Quote:
    trade_date: str
    board: str
    code: str
    name: str
    currency: str
    previous_close: str
    closing_price: str
    ask: str
    bid: str
    high: str
    low: str
    shares_traded: str
    turnover: str
    status: str


def sheet_urls(day: date, board: str) -> list[str]:
    stamp = day.strftime("%y%m%d")
    filename = f"d{stamp}e.htm" if board == "Main Board" else f"e_G{stamp}.htm"
    subdir = "" if board == "Main Board" else "/GEM"
    return [
        f"{BASE_URL}/dayquot{subdir}/{filename}",
        f"{BASE_URL}/dayquot_12m{subdir}/{filename}",
    ]


def download(url: str, retries: int = 3) -> str:
    return scrape_url(url, proxy_pool="premium", successful_status_codes=[404, 410])


def get_sheet(day: date, board: str) -> tuple[str, str]:
    for url in sheet_urls(day, board):
        try:
            return download(url), url
        except HTTPError as exc:
            if exc.code not in (404, 410):
                raise RuntimeError(f"HKEX returned HTTP {exc.code} for {url}") from exc
    raise FileNotFoundError(f"no {board} quotation sheet for {day.isoformat()}")


def clean_number(value: str) -> str:
    return "" if value in {"-", "N/A"} else value.replace(",", "")


def parse_sheet(document: str, day: date, board: str) -> list[Quote]:
    text = html.unescape(re.sub(r"<[^>]+>", "", document)).replace("\r", "")
    match = re.search(
        r"\n\s*QUOTATIONS\s*\n.*?TURNOVER \(\$\)\s*\n(?P<body>.*?)"
        r"\n-+\s*\n\s*SALES RECORDS FOR ALL STOCKS",
        text,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError(f"could not locate the QUOTATIONS table in the {board} sheet")

    lines = [line.rstrip() for line in match.group("body").splitlines() if line.strip()]
    first_line = re.compile(
        rf"^\s*(?P<code>\d{{1,5}})\s+(?P<name>.+?)\s{{2,}}"
        rf"(?P<currency>[A-Z]{{3}})\s+(?P<rest>.+?)\s*$"
    )
    values = re.compile(rf"^{NUMBER}\s+{NUMBER}\s+{NUMBER}\s+{NUMBER}$")
    rows: list[Quote] = []
    index = 0

    while index < len(lines):
        found = first_line.match(lines[index])
        if not found:
            index += 1
            continue
        rest = found.group("rest")
        status = ""
        previous = closing = ask = bid = high = low = shares = turnover = ""

        if "SUSPENDED" in rest.upper():
            status = rest.strip()
            index += 1
        elif values.match(rest) and index + 1 < len(lines):
            top = rest.split()
            bottom = lines[index + 1].split()
            if len(bottom) != 4 or not values.match(" ".join(bottom)):
                index += 1
                continue
            previous, ask, high, shares = map(clean_number, top)
            closing, bid, low, turnover = map(clean_number, bottom)
            index += 2
        else:
            index += 1
            continue

        rows.append(
            Quote(
                trade_date=day.isoformat(), board=board, code=found.group("code").zfill(5),
                name=" ".join(found.group("name").split()), currency=found.group("currency"),
                previous_close=previous, closing_price=closing, ask=ask, bid=bid,
                high=high, low=low, shares_traded=shares, turnover=turnover, status=status,
            )
        )

    if not rows:
        raise ValueError(f"no quote rows parsed from the {board} sheet")
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch official HKEX end-of-day prices.")
    parser.add_argument("--date", type=date.fromisoformat, help="trade date (YYYY-MM-DD); default: today in Hong Kong")
    parser.add_argument("--output", type=Path, help="CSV path; default: hkex_prices_YYYY-MM-DD.csv")
    parser.add_argument("--board", choices=("all", "main", "gem"), default="all")
    parser.add_argument("--lookback", type=int, default=7, help="days to look back when --date is omitted (default: 7)")
    return parser.parse_args()


def upload_to_s3(csv_path: Path) -> str:
    destination = f"{S3_PREFIX}{csv_path.name}"
    try:
        subprocess.run(
            ["aws", "s3", "cp", str(csv_path), destination, "--only-show-errors"],
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("AWS CLI is not installed or is not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"AWS CLI upload failed with exit code {exc.returncode}") from exc
    return destination


def main() -> int:
    args = parse_args()
    if args.lookback < 0:
        raise SystemExit("--lookback must be zero or greater")

    requested = args.date or datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
    candidates = [requested] if args.date else [requested - timedelta(days=n) for n in range(args.lookback + 1)]
    boards = {"all": ("Main Board", "GEM"), "main": ("Main Board",), "gem": ("GEM",)}[args.board]

    selected: date | None = None
    documents: dict[str, tuple[str, str]] = {}
    for candidate in candidates:
        try:
            documents[boards[0]] = get_sheet(candidate, boards[0])
            selected = candidate
            break
        except FileNotFoundError:
            continue
    if selected is None:
        print(f"error: no HKEX quotation sheet found from {candidates[-1]} through {requested}", file=sys.stderr)
        return 1

    quotes: list[Quote] = []
    sources: list[str] = []
    for board in boards:
        try:
            document, url = documents.get(board) or get_sheet(selected, board)
        except FileNotFoundError as exc:
            print(f"warning: {exc}", file=sys.stderr)
            continue
        quotes.extend(parse_sheet(document, selected, board))
        sources.append(url)

    try:
        excluded_codes = load_excluded_codes()
        unfiltered_count = len(quotes)
        quotes = filter_by_code(quotes, excluded_codes)
    except (RuntimeError, ValueError) as exc:
        print(f"error: could not clean CSV data: {exc}", file=sys.stderr)
        return 1

    output = args.output or Path(f"hkex_prices_{selected.isoformat()}.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_rows = enrich_rows(asdict(quote) for quote in quotes)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: could not enrich cross-listed prices: {exc}", file=sys.stderr)
        return 1

    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(Quote.__dataclass_fields__) + enrichment_columns(),
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Wrote {len(quotes):,} quotes for {selected} to {output}")
    print(f"Removed {unfiltered_count - len(quotes):,} excluded rows")
    for source in sources:
        print(f"Source: {source}")
    try:
        destination = upload_to_s3(output)
    except RuntimeError as exc:
        print(f"error: CSV was created locally, but S3 upload failed: {exc}", file=sys.stderr)
        return 1
    print(f"Uploaded to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
