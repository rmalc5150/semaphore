#!/usr/bin/env python3
"""Collect biotech licensing, M&A, JV, milestone, and royalty transactions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus

from clinicaltrials_studies import parse_date, period_bounds
from people_movements import clean, clean_entity, load_jsonl, parse_datetime, parse_feed, request


S3_PREFIX = "s3://processed-059416028963-us-east-1-an/strategic-transactions/"

CATEGORY_RULES = {
    "licensing_agreement": (
        r"\b(?:licen[cs](?:e[sd]?|ing)|in-licen[cs]e|out-licen[cs]e|exclusive rights|commerciali[sz]ation rights)\b",
        'biotech ("license agreement" OR "licensing agreement" OR "exclusive license" OR "commercialization rights")',
    ),
    "acquisition": (
        r"\b(?:acquir(?:e[sd]?|ing|er)|acquisition|merger|takeover|buyout|tender offer)\b",
        'biotech (acquires OR acquisition OR merger OR takeover OR buyout)',
    ),
    "joint_venture": (
        r"\b(?:joint venture|JV|jointly (?:establish|form|launch)|co-owned company)\b",
        'biotech ("joint venture" OR "forms JV" OR "launches JV")',
    ),
    "milestone_payment": (
        r"\b(?:milestone payments?|milestone achieved|earns? milestone|triggers? (?:a )?milestone|development milestone|regulatory milestone|commercial milestone)\b",
        'biotech ("milestone payment" OR "milestone achieved" OR "earns milestone" OR "triggers milestone")',
    ),
    "royalty_agreement": (
        r"\b(?:royalt(?:y|ies)|royalty financing|royalty agreement|royalty interest|revenue interest)\b",
        'biotech ("royalty agreement" OR "royalty financing" OR royalties OR "royalty interest")',
    ),
}

MONEY = re.compile(
    r"(?P<currency>US\$|CNY|RMB|CN¥|HK\$|€|EUR|£|GBP|\$)\s*"
    r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<scale>billion|million|thousand|bn|mm|m|b)?",
    re.I,
)
PARTY_PATTERNS = (
    re.compile(r"^(?P<a>[A-Z][^:;|]{1,80}?)\s+(?:and|&|with)\s+(?P<b>[A-Z][^:;|]{1,80}?)\s+(?:enter|sign|announce|form|launch|establish)", re.I),
    re.compile(r"^(?P<a>[A-Z][^:;|]{1,80}?)\s+(?:to acquire|acquires?|buys?|merges with)\s+(?P<b>[A-Z][^:;|]{1,80}?)(?=\s+(?:for|in|to|under)\b|[,:;|]|$)", re.I),
    re.compile(r"^(?P<a>[A-Z][^:;|]{1,80}?)\s+(?:licenses?|licen[cs]es)\s+[^:;]{0,80}?\s+(?:to|from)\s+(?P<b>[A-Z][^:;|]{1,80}?)(?=[,:;|]|$)", re.I),
)
BIOTECH_RELEVANCE = re.compile(
    r"\b(biotech|biopharma|pharma(?:ceutical)?|therapeutics?|biosciences?|life sciences?|drug|"
    r"clinical|medical|medicine|diagnostic|oncology|cancer|antibody|vaccine|gen(?:e|ome|omic)|"
    r"RNA|protein|cell therap|health|Novartis|Pfizer|Merck|Sanofi|Takeda|AstraZeneca|"
    r"Johnson\s*&\s*Johnson|J&J|Roche|AbbVie|Amgen|GSK|Eli Lilly|Bristol Myers)\b",
    re.I,
)


def money_values(text: str) -> list[dict[str, Any]]:
    scale_values = {"billion": 1_000_000_000, "bn": 1_000_000_000, "b": 1_000_000_000,
                    "million": 1_000_000, "mm": 1_000_000, "m": 1_000_000, "thousand": 1_000}
    currencies = {"$": "USD", "US$": "USD", "CNY": "CNY", "RMB": "CNY", "CN¥": "CNY",
                  "HK$": "HKD", "€": "EUR", "EUR": "EUR", "£": "GBP", "GBP": "GBP"}
    result = []
    for match in MONEY.finditer(text):
        raw = match.group(0)
        scale = (match.group("scale") or "").lower()
        amount = float(match.group("amount")) * scale_values.get(scale, 1)
        context = text[max(0, match.start() - 45): min(len(text), match.end() + 45)].lower()
        kind = "upfront" if "upfront" in context or "up-front" in context else "milestone" if "milestone" in context else "transaction_value" if any(word in context for word in ("deal", "transaction", "acquisition", "valued")) else "unspecified"
        result.append({"type": kind, "currency": currencies[match.group("currency")], "amount": int(amount) if amount.is_integer() else amount, "raw": raw})
    return result


def categories(text: str, explicit: Any = None) -> list[str]:
    aliases = {"licensing": "licensing_agreement", "license": "licensing_agreement", "acquisitions": "acquisition",
               "joint venture": "joint_venture", "milestone": "milestone_payment", "royalty": "royalty_agreement"}
    supplied = [explicit] if isinstance(explicit, str) else explicit if isinstance(explicit, list) else []
    normalized = {aliases.get(str(value).lower().replace("-", " "), str(value).lower().replace("-", "_")) for value in supplied}
    normalized.update(name for name, (pattern, _) in CATEGORY_RULES.items() if re.search(pattern, text, re.I))
    return sorted(normalized & set(CATEGORY_RULES))


def parties(text: str, record: dict[str, Any]) -> list[str]:
    supplied = record.get("parties")
    if isinstance(supplied, list):
        return [value for value in (clean_entity(item) for item in supplied) if value]
    for pattern in PARTY_PATTERNS:
        match = pattern.search(text)
        if match:
            return [value for value in (clean_entity(match.group("a")), clean_entity(match.group("b"))) if value]
    return []


def extract(record: dict[str, Any]) -> dict[str, Any] | None:
    title = clean(record.get("title")); body = clean(record.get("text") or record.get("summary"))
    text = f"{title}. {body}".strip()
    explicit_categories = record.get("categories") or record.get("category")
    kinds = categories(text, explicit_categories)
    if not kinds:
        return None
    if not explicit_categories and str(record.get("source", "")).startswith("Google News") and not BIOTECH_RELEVANCE.search(text):
        return None
    event_time = parse_datetime(record.get("publishedAt") or record.get("date") or record.get("eventDate"))
    event_date = str(record.get("eventDate") or "")[:10] or (event_time.date().isoformat() if event_time else None)
    counterparties = parties(title, record)
    economics = money_values(text)
    royalty = None
    royalty_match = re.search(r"(?P<rate>\d+(?:\.\d+)?)\s*%\s+(?:tiered\s+)?royalt", text, re.I)
    if royalty_match:
        royalty = {"ratePct": float(royalty_match.group("rate")), "description": royalty_match.group(0)}
    assets = record.get("assets") if isinstance(record.get("assets"), list) else []
    geography = record.get("geography")
    completeness = 25 + (20 if counterparties else 0) + (15 if economics or royalty else 0) + (10 if event_date else 0) + (10 if assets else 0)
    key = "|".join(("+".join(kinds), "|".join(sorted(p.lower() for p in counterparties)), event_date or "", re.sub(r"\W", "", title.lower())))
    status = clean(record.get("status")) or (
        "completed" if re.search(r"\b(completes?|completed|closes?|closed|completion of)\b", text, re.I)
        else "terminated" if re.search(r"\b(terminates?|terminated|abandons?|withdraws?|backs? off|falls? through)\b", text, re.I)
        else "rumored" if re.search(r"\b(reportedly|rumou?r|considering|eyes?|potential target)\b", text, re.I)
        else "proposed" if re.search(r"\b(to acquire|plans? to|proposes?|definitive agreement)\b", text, re.I)
        else "announced"
    )
    return {
        "transactionId": hashlib.sha256(key.encode()).hexdigest()[:20], "categories": kinds,
        "eventDate": event_date, "status": status,
        "parties": counterparties, "assets": assets, "therapeuticAreas": record.get("therapeuticAreas", []),
        "geography": geography, "economics": economics, "royalty": royalty,
        "confidence": min(100, completeness),
        "evidence": [{"source": clean(record.get("source")) or "unknown", "url": record.get("url"),
                      "publishedAt": event_time.isoformat() if event_time else None, "title": title}],
    }


def merge(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    # Prefer a semantic key when two publishers use slightly different titles.
    semantic: dict[tuple[Any, ...], str] = {}
    for item in items:
        parties_key = tuple(sorted(p.lower() for p in item["parties"]))
        sem = (tuple(item["categories"]), parties_key, item.get("eventDate")) if parties_key else None
        key = semantic.get(sem) if sem else None
        key = key or item["transactionId"]
        if key not in result:
            result[key] = item
            if sem: semantic[sem] = key
            continue
        current = result[key]
        seen = {(e.get("source"), e.get("url")) for e in current["evidence"]}
        current["evidence"].extend(e for e in item["evidence"] if (e.get("source"), e.get("url")) not in seen)
        current["categories"] = sorted(set(current["categories"]) | set(item["categories"]))
        current["confidence"] = min(100, max(current["confidence"], item["confidence"]) + 5 * (len(current["evidence"]) - 1))
    return sorted(result.values(), key=lambda x: (x.get("eventDate") or "", x["transactionId"]), reverse=True)


def news_search(start: date, end: date) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, Any]]]:
    records, errors, runs = [], [], []
    exclusive_end = end + timedelta(days=1)
    for category, (_, query) in CATEGORY_RULES.items():
        dated = f"{query} after:{start.isoformat()} before:{exclusive_end.isoformat()}"
        url = f"https://news.google.com/rss/search?q={quote_plus(dated)}&hl=en-US&gl=US&ceid=US:en"
        source = f"Google News {category}"
        try:
            rows = parse_feed(request(url), source); records.extend(rows)
            runs.append({"source": source, "mode": "bounded_news_search", "recordCount": len(rows), "status": "ok"})
        except Exception as exc:
            errors.append({"source": source, "url": url, "error": str(exc)})
            runs.append({"source": source, "mode": "bounded_news_search", "recordCount": 0, "status": "error"})
    unique = {(row.get("url"), row.get("title")): row for row in records}
    return list(unique.values()), errors, runs


def write(payload: dict[str, Any], destination: str) -> None:
    if destination.startswith("s3://"):
        process = subprocess.Popen(["aws", "s3", "cp", "-", destination, "--only-show-errors"], stdin=subprocess.PIPE, text=True, encoding="utf-8")
        assert process.stdin is not None
        json.dump(payload, process.stdin, ensure_ascii=False, indent=2); process.stdin.write("\n"); process.stdin.close()
        if process.wait(): raise RuntimeError("AWS CLI upload failed")
    else:
        Path(destination).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("daily", "historical"):
        from disclosure_collection import main as shared_main
        return shared_main("strategic-transactions")
    parser = argparse.ArgumentParser(description="Collect biotech strategic transactions and payment events.")
    parser.add_argument("period", choices=("day", "month")); parser.add_argument("date", type=parse_date)
    parser.add_argument("--input-jsonl", action="append", type=Path, default=[])
    parser.add_argument("--no-news-search", action="store_true")
    parser.add_argument("--output", help="local path or s3:// URI")
    args = parser.parse_args(); start, end = period_bounds(args.period, args.date)
    records: list[dict[str, Any]] = []; errors = []; runs = []
    if not args.no_news_search:
        rows, found_errors, found_runs = news_search(start, end)
        records.extend(rows); errors.extend(found_errors); runs.extend(found_runs)
    try:
        for path in args.input_jsonl:
            rows = load_jsonl(path); records.extend(rows)
            runs.append({"source": str(path), "mode": "structured_input", "recordCount": len(rows), "status": "ok"})
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 1
    candidates = []
    for record in records:
        stamp = parse_datetime(record.get("publishedAt") or record.get("date") or record.get("eventDate"))
        if stamp is None or start <= stamp.date() <= end:
            item = extract(record)
            if item: candidates.append(item)
    transactions = merge(candidates)
    counts = {category: sum(category in item["categories"] for item in transactions) for category in CATEGORY_RULES}
    coverage = "failed" if not records else "complete" if runs and all(run["status"] == "ok" for run in runs) else "partial"
    payload = {"schemaVersion": 1, "period": args.period, "startDate": str(start), "endDate": str(end),
               "generatedAt": datetime.now(timezone.utc).isoformat(), "coverageStatus": coverage,
               "sourceRuns": runs, "sourceErrors": errors, "recordCount": len(records),
               "transactionCount": len(transactions), "categoryCounts": counts, "transactions": transactions,
               "methodology": {"note": "Rule-based candidate extraction; review linked evidence before treating a transaction or amount as confirmed.",
                               "multiLabel": "One transaction may be both a licensing and royalty agreement or create later milestone-payment events.",
                               "amounts": "Amounts retain their type and currency and are never summed across currencies."}}
    key = f"strategic_transactions_{args.period}_{start}_{end}.json"; destination = args.output or S3_PREFIX + key
    try: write(payload, destination)
    except (OSError, RuntimeError) as exc: print(f"error: {exc}", file=sys.stderr); return 1
    print(f"Wrote {len(transactions)} transactions to {destination}")
    print(f"Coverage: {coverage}; fetched {len(records)} candidate records; categories: {counts}")
    if errors: print(f"warning: {len(errors)} source(s) failed; see sourceErrors", file=sys.stderr)
    if coverage == "failed": print("error: no source returned records; output is not evidence of zero transactions", file=sys.stderr); return 2
    return 0


if __name__ == "__main__": raise SystemExit(main())
