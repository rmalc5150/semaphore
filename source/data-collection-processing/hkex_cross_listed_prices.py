#!/usr/bin/env python3
"""Add same-date foreign-listing OHLCV prices to HKEX price CSV rows.

Cross-listings are accepted only from a reviewed mapping CSV. Price data is
retrieved from Yahoo Finance's chart endpoint using the mapped ticker symbol.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


DEFAULT_MAPPING = Path(__file__).with_name("hkex_cross_listings.csv")
EXCHANGES = ("NASDAQ", "NYSE", "STAR", "SHENZHEN")
PRICE_FIELDS = ("symbol", "currency", "open", "high", "low", "close", "adjusted_close", "volume")
USER_AGENT = "Mozilla/5.0 (compatible; hkex-cross-listed-prices/1.0)"


def normalize_hkex_code(value: str) -> str:
    value = value.strip()
    if not value.isdigit() or len(value) > 5:
        raise ValueError(f"invalid HKEX code: {value!r}")
    return value.zfill(5)


def load_mapping(path: Path = DEFAULT_MAPPING) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"hkex_code", "exchange", "symbol"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path} must contain columns: {', '.join(sorted(required))}")
        for line_number, row in enumerate(reader, start=2):
            code = normalize_hkex_code(row["hkex_code"])
            exchange = row["exchange"].strip().upper()
            symbol = row["symbol"].strip().upper()
            if exchange not in EXCHANGES:
                raise ValueError(f"unsupported exchange {exchange!r} on line {line_number}")
            if not symbol:
                raise ValueError(f"missing symbol on line {line_number}")
            if exchange in mapping.setdefault(code, {}):
                raise ValueError(f"duplicate {exchange} mapping for HKEX code {code}")
            mapping[code][exchange] = symbol
    return mapping


def fetch_daily_price(symbol: str, trade_date: date) -> dict[str, str]:
    start = datetime.combine(trade_date - timedelta(days=2), time.min, timezone.utc)
    end = datetime.combine(trade_date + timedelta(days=3), time.min, timezone.utc)
    query = urlencode({
        "period1": int(start.timestamp()),
        "period2": int(end.timestamp()),
        "interval": "1d",
        "events": "history",
    })
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?{query}"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"price request for {symbol} returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"price request for {symbol} failed: {exc}") from exc

    chart = payload.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"price request for {symbol} failed: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        return {}
    result = results[0]
    meta = result.get("meta", {})
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators", {})
    quotes = (indicators.get("quote") or [{}])[0]
    adjusted = (indicators.get("adjclose") or [{}])[0].get("adjclose", [])
    try:
        market_zone = ZoneInfo(meta.get("exchangeTimezoneName", "UTC"))
    except Exception:
        market_zone = ZoneInfo("UTC")

    for index, timestamp in enumerate(timestamps):
        actual_date = datetime.fromtimestamp(timestamp, timezone.utc).astimezone(market_zone).date()
        if actual_date != trade_date:
            continue

        def value(field: str) -> str:
            values = quotes.get(field) or []
            item = values[index] if index < len(values) else None
            return "" if item is None else str(item)

        adj = adjusted[index] if index < len(adjusted) else None
        return {
            "symbol": symbol,
            "currency": str(meta.get("currency", "")),
            "open": value("open"),
            "high": value("high"),
            "low": value("low"),
            "close": value("close"),
            "adjusted_close": "" if adj is None else str(adj),
            "volume": value("volume"),
        }
    return {}


def enrichment_columns() -> list[str]:
    return [f"{exchange.lower()}_{field}" for exchange in EXCHANGES for field in PRICE_FIELDS]


def enrich_rows(
    rows: Iterable[dict[str, str]], mapping_path: Path = DEFAULT_MAPPING
) -> list[dict[str, str]]:
    mapping = load_mapping(mapping_path)
    cache: dict[tuple[str, date], dict[str, str]] = {}
    enriched: list[dict[str, str]] = []
    for original in rows:
        row = dict(original)
        for column in enrichment_columns():
            row[column] = ""
        code = normalize_hkex_code(row["code"])
        trade_date = date.fromisoformat(row["trade_date"])
        for exchange, symbol in mapping.get(code, {}).items():
            key = (symbol, trade_date)
            if key not in cache:
                cache[key] = fetch_daily_price(symbol, trade_date)
            price = cache[key]
            # Preserve the verified symbol even when that exchange was closed that day.
            row[f"{exchange.lower()}_symbol"] = symbol
            for field, value in price.items():
                row[f"{exchange.lower()}_{field}"] = value
        enriched.append(row)
    return enriched


def enrich_csv(input_path: Path, output_path: Path, mapping_path: Path = DEFAULT_MAPPING) -> tuple[int, int]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"code", "trade_date"}.issubset(reader.fieldnames):
            raise ValueError(f"{input_path} must contain 'code' and 'trade_date' columns")
        rows = list(reader)
    enriched = enrich_rows(rows, mapping_path)
    fields = list(reader.fieldnames) + [c for c in enrichment_columns() if c not in reader.fieldnames]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(enriched)
    matched = sum(any(row[f"{exchange.lower()}_symbol"] for exchange in EXCHANGES) for row in enriched)
    return len(enriched), matched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add foreign-listing prices to an HKEX CSV.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, help="output CSV; default: replace input")
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or args.input
    try:
        count, matched = enrich_csv(args.input, output, args.mapping)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {count:,} rows to {output}; enriched {matched:,} cross-listed companies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
