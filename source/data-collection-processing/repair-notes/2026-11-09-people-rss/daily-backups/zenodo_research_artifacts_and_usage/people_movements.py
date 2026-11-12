#!/usr/bin/env python3
"""Collect and score biotech personnel movements from public evidence.

The collector deliberately does not scrape LinkedIn or paywalled publications.
It accepts RSS/Atom feeds and newline-delimited JSON exported from licensed or
internal sources, normalizes every item into the same evidence-backed schema,
and can write either a local JSON file or the project's S3 data lake.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from clinicaltrials_studies import parse_date, period_bounds


S3_PREFIX = "s3://processed-059416028963-us-east-1-an/people-movements/"
USER_AGENT = "biotech-people-movement-collector/1.0 (mailto:data@example.com)"
DEFAULT_FEEDS = {
    "BioSpace": "https://www.biospace.com/all-news.rss",
    "BioSpace Job Trends": "https://www.biospace.com/job-trends.rss",
    "Fierce Biotech": "https://www.fiercebiotech.com/rss/biotech/xml",
}
HISTORICAL_QUERIES = (
    'biotech (appoints OR appointed OR joins OR joined OR hires OR named) (scientist OR "chief scientific officer" OR "chief medical officer" OR "head of" OR "research")',
    'biopharma (appoints OR appointed OR joins OR joined OR hires OR named) (scientist OR "chief scientific officer" OR "chief medical officer" OR "head of" OR "research")',
    '(pharmaceutical OR therapeutics) (appoints OR appointed OR joins OR joined OR hires OR named) (CSO OR CMO OR scientist OR "head of research")',
    '(生物医药 OR 生物科技 OR 制药) (任命 OR 加入 OR 聘任 OR 首席科学官 OR 研发人员)',
)

MOVE_WORDS = re.compile(
    r"\b(appoint(?:s|ed)?|join(?:s|ed)?|hire(?:s|d)?|name[sd]?|promot(?:e[sd]?|ed)|"
    r"depart(?:s|ed|ure)?|leave[sd]?|step(?:s|ped)[ -](?:down|in)|resign(?:s|ed|ation)?)\b",
    re.I,
)
NAME = r"(?P<person>[A-Z][A-Za-z'’-]+(?:\s+(?:[A-Z]\.|[A-Z][A-Za-z'’-]+)){1,3})"
ORG = r"(?P<__NAME__>[A-Z][A-Za-z0-9&.,'’+\- ]{1,80}?)"
ROLE = r"(?P<role>(?:(?:chief|senior|executive|associate|vice|global|head|director|principal|lead|president)[^.;]{1,90}?))(?=\.|;|$)"

PATTERNS = (
    re.compile(NAME + r"\s+(?:leaves?|left|departed)\s+" + ORG.replace("__NAME__", "old") + r"\s+(?:to join|for)\s+(?P<new>[A-Z][A-Za-z0-9&.,'’+\- ]{1,80}?)(?=\s+as\b|[.;]|$)(?:\s+as\s+" + ROLE + r")?", re.I),
    re.compile(ORG.replace("__NAME__", "new") + r"\s+(?:appoints?|names?|hires?)\s+" + NAME + r"\s+(?:as|to serve as)\s+" + ROLE, re.I),
    re.compile(NAME + r"\s+(?:joins?|joined)\s+" + ORG.replace("__NAME__", "new") + r"\s+as\s+" + ROLE, re.I),
    re.compile(NAME + r"\s+(?:has been |was )?(?:named|appointed|promoted to)\s+" + ROLE + r"\s+(?:at|of)\s+" + ORG.replace("__NAME__", "new"), re.I),
)

OLD_ORG_PATTERNS = (
    re.compile(r"(?:previously|formerly)\s+(?:served|worked)?\s*(?:as\s+[^,.]{1,100}\s+)?(?:at|with)\s+([A-Z][A-Za-z0-9&.,'’+\- ]{1,80}?)(?=\s+(?:with|and)\s+|[.;]|$)", re.I),
    re.compile(r"(?:comes|joins|joined)\s+(?:to\s+\w+\s+)?from\s+([A-Z][A-Za-z0-9&.,'’+\- ]{1,80}?)(?=\s+(?:with|and)\s+|[.;]|$)", re.I),
)

TITLE_WEIGHTS = (
    (re.compile(r"\b(chief|ceo|cso|cmo|cto|cfo|president)\b", re.I), 30, "C-suite"),
    (re.compile(r"\b(svp|senior vice president|executive vice president|evp)\b", re.I), 24, "SVP/EVP"),
    (re.compile(r"\b(vp|vice president|head of)\b", re.I), 18, "VP/Head"),
    (re.compile(r"\b(director|principal scientist)\b", re.I), 12, "Director/Principal"),
)

EXPERTISE = {
    "oncology": r"\b(oncol(?:ogy|ogist)|cancer|tumou?r)\b",
    "antibody-drug conjugates": r"\b(ADC|antibody.drug conjugate)s?\b",
    "cell therapy": r"\b(CAR[ -]?T|cell therap(?:y|ies))\b",
    "gene therapy": r"\b(gene therap(?:y|ies)|gene editing|CRISPR)\b",
    "targeted protein degradation": r"\b(targeted protein degradation|TPD|PROTAC)s?\b",
    "immunology": r"\b(immunology|autoimmune|inflammation)\b",
    "neuroscience": r"\b(neuroscience|neurology|CNS)\b",
    "clinical development": r"\b(clinical development|clinical research|medical affairs)\b",
    "drug discovery": r"\b(drug discovery|medicinal chemistry|translational medicine)\b",
}

R_AND_D_ROLE = re.compile(
    r"\b(CSO|CMO|CTO|chief (?:scientific|medical|technology|research|development) officer|"
    r"research|scientist|science|R&D|discovery|preclinical|clinical|translational|"
    r"medicinal chemistry|biology|bioinformatics|pharmacology|toxicology|oncology|"
    r"immunology|genomics|platform|pipeline|drug development)\b",
    re.I,
)


def clean(value: Any) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip(" \t\r\n,.;:-")


def clean_entity(value: Any) -> str | None:
    result = clean(value)
    result = re.split(r"\s+-\s+", result, maxsplit=1)[0]
    result = re.split(r"\s+(?:today|announces?|which|where|who|after|effective|and\s+(?:brings?|will|has))\b", result, maxsplit=1, flags=re.I)[0]
    return result.strip(" ,.;:-") or None


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def request(url: str, retries: int = 3) -> bytes:
    req = Request(url, headers={"Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml", "User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=60) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"could not fetch {url}: {exc}") from exc
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def child_text(element: ET.Element, names: Iterable[str]) -> str:
    wanted = set(names)
    for child in element.iter():
        if child.tag.rsplit("}", 1)[-1] in wanted and child.text:
            return clean(child.text)
    return ""


def parse_feed(payload: bytes, source: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError(f"{source} returned invalid RSS/Atom XML: {exc}") from exc
    entries = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] in ("item", "entry")]
    records = []
    for entry in entries:
        link = child_text(entry, ("link",))
        if not link:
            for node in entry.iter():
                if node.tag.rsplit("}", 1)[-1] == "link" and node.attrib.get("href"):
                    link = node.attrib["href"]
                    break
        records.append({
            "source": source,
            "title": child_text(entry, ("title",)),
            "text": child_text(entry, ("description", "summary", "content")),
            "url": link or child_text(entry, ("guid", "id")),
            "publishedAt": child_text(entry, ("pubDate", "published", "updated", "date")),
        })
    return records


def historical_news(start: date, end: date) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Search Google News' public RSS endpoint using an explicit month window."""
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    exclusive_end = end + timedelta(days=1)
    for index, query in enumerate(HISTORICAL_QUERIES, 1):
        dated_query = f"{query} after:{start.isoformat()} before:{exclusive_end.isoformat()}"
        language = "zh-CN&gl=CN&ceid=CN:zh-Hans" if index == len(HISTORICAL_QUERIES) else "en-US&gl=US&ceid=US:en"
        url = f"https://news.google.com/rss/search?q={quote_plus(dated_query)}&hl={language}"
        source = f"Google News historical search {index}"
        try:
            records.extend(parse_feed(request(url), source))
        except Exception as exc:
            errors.append({"source": source, "url": url, "error": str(exc)})
    # The query occasionally returns syndications more than once.
    unique = {(item.get("url"), item.get("title")): item for item in records}
    return list(unique.values()), errors


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{number}: expected a JSON object")
            item.setdefault("source", path.stem)
            records.append(item)
    return records


def seniority(role: str | None) -> tuple[int, str | None]:
    for pattern, points, label in TITLE_WEIGHTS:
        if pattern.search(role or ""):
            return points, label
    return (7, "Other") if role else (0, None)


def canonical(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def extract(record: dict[str, Any]) -> dict[str, Any] | None:
    title, body = clean(record.get("title")), clean(record.get("text") or record.get("summary"))
    text = f"{title}. {body}".strip()
    explicit = any(record.get(field) for field in ("person", "newOrganization", "oldOrganization"))
    if not explicit and not MOVE_WORDS.search(text):
        return None
    fields: dict[str, Any] = {}
    matched_pattern = None
    for index, pattern in enumerate(PATTERNS, 1):
        match = pattern.search(text)
        if match:
            fields = {key: clean_entity(value) for key, value in match.groupdict().items() if value}
            matched_pattern = index
            break
    person = clean_entity(record.get("person")) or fields.get("person")
    new_org = clean_entity(record.get("newOrganization")) or fields.get("new")
    old_org = clean_entity(record.get("oldOrganization")) or fields.get("old")
    role = clean_entity(record.get("role")) or fields.get("role")
    if not old_org:
        for pattern in OLD_ORG_PATTERNS:
            match = pattern.search(text)
            if match:
                old_org = clean_entity(match.group(1))
                break
    if not person or (not new_org and not old_org):
        return None
    published = parse_datetime(record.get("publishedAt") or record.get("date"))
    event_date = str(record.get("eventDate") or "")[:10] or (published.date().isoformat() if published else None)
    expertise = sorted({label for label, pattern in EXPERTISE.items() if re.search(pattern, text, re.I)})
    rank_points, rank = seniority(role)
    corroborated = max(1, int(record.get("corroboratingSources", 1) or 1))
    completeness = 20 if old_org and new_org else 10
    confidence = min(100, 35 + completeness + (15 if role else 0) + (10 if event_date else 0) + min(20, (corroborated - 1) * 10))
    direction = "move" if old_org and new_org else "arrival" if new_org else "departure"
    identity = "|".join((canonical(person), canonical(old_org), canonical(new_org), canonical(role), event_date or ""))
    return {
        "movementId": hashlib.sha256(identity.encode()).hexdigest()[:20],
        "person": person,
        "oldOrganization": old_org,
        "newOrganization": new_org,
        "role": role,
        "direction": direction,
        "eventDate": event_date,
        "seniority": rank,
        "expertise": expertise,
        "assets": list(record.get("assets", [])),
        "confidence": confidence,
        "signalScore": min(100, rank_points + completeness + min(20, len(expertise) * 5) + min(20, corroborated * 5)),
        "evidence": [{"source": clean(record.get("source")) or "unknown", "url": record.get("url"), "publishedAt": published.isoformat() if published else None, "title": title, "extractionPattern": matched_pattern}],
    }


def merge_movements(movements: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in movements:
        key = item["movementId"]
        if key not in merged:
            merged[key] = item
            continue
        current = merged[key]
        seen = {(e.get("source"), e.get("url")) for e in current["evidence"]}
        current["evidence"].extend(e for e in item["evidence"] if (e.get("source"), e.get("url")) not in seen)
        count = len(current["evidence"])
        current["confidence"] = min(100, current["confidence"] + min(20, (count - 1) * 10))
        current["signalScore"] = min(100, current["signalScore"] + min(15, (count - 1) * 5))
    return sorted(merged.values(), key=lambda x: (x.get("eventDate") or "", x["person"], x["movementId"]), reverse=True)


def clusters(movements: list[dict[str, Any]], window_days: int = 180, minimum: int = 2) -> list[dict[str, Any]]:
    by_org: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in movements:
        if item.get("newOrganization") and item.get("eventDate"):
            by_org[item["newOrganization"]].append(item)
    result = []
    for organization, items in by_org.items():
        dated = sorted(items, key=lambda x: x["eventDate"])
        best: list[dict[str, Any]] = []
        for left, start in enumerate(dated):
            end = date.fromisoformat(start["eventDate"]) + timedelta(days=window_days)
            group = [item for item in dated[left:] if date.fromisoformat(item["eventDate"]) <= end]
            if len(group) > len(best):
                best = group
        if len(best) < minimum:
            continue
        sources = sorted({e["source"] for item in best for e in item["evidence"]})
        expertise = sorted({tag for item in best for tag in item["expertise"]})
        score = min(100, 15 * len(best) + 8 * len({canonical(item.get("oldOrganization")) for item in best if item.get("oldOrganization")}) + 4 * len(expertise) + 3 * len(sources))
        result.append({"organization": organization, "startDate": best[0]["eventDate"], "endDate": best[-1]["eventDate"], "movementCount": len(best), "people": [item["person"] for item in best], "sourceOrganizations": sorted({item["oldOrganization"] for item in best if item.get("oldOrganization")}), "expertise": expertise, "evidenceSources": sources, "clusterScore": score})
    return sorted(result, key=lambda x: (x["clusterScore"], x["movementCount"]), reverse=True)


def workforce_trends(movements: list[dict[str, Any]], records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classify company R&D staffing direction without conflating intent and fact.

    Structured input records can carry organization, researchHeadcount, asOfDate,
    source, and url. Two headcount observations take precedence over inferred
    movement flow. Inferred results require at least two net R&D movements.
    """
    snapshots: dict[str, list[dict[str, Any]]] = defaultdict(list)
    display_names: dict[str, str] = {}
    for record in records:
        organization = clean_entity(record.get("organization"))
        count = record.get("researchHeadcount")
        as_of = str(record.get("asOfDate") or record.get("date") or "")[:10]
        if not organization or isinstance(count, bool) or not isinstance(count, (int, float)) or count < 0:
            continue
        try:
            date.fromisoformat(as_of)
        except ValueError:
            continue
        key = canonical(organization)
        display_names[key] = organization
        snapshots[key].append({"asOfDate": as_of, "researchHeadcount": int(count), "source": clean(record.get("source")) or "unknown", "url": record.get("url")})

    flow: dict[str, dict[str, Any]] = defaultdict(lambda: {"arrivals": [], "departures": []})
    for item in movements:
        if not (item.get("expertise") or R_AND_D_ROLE.search(item.get("role") or "")):
            continue
        for field, direction in (("newOrganization", "arrivals"), ("oldOrganization", "departures")):
            organization = item.get(field)
            if organization:
                key = canonical(organization)
                display_names.setdefault(key, organization)
                flow[key][direction].append(item["movementId"])

    results = []
    for key in sorted(set(snapshots) | set(flow)):
        observations = sorted(snapshots.get(key, []), key=lambda x: x["asOfDate"])
        arrivals = flow[key]["arrivals"]
        departures = flow[key]["departures"]
        net = len(arrivals) - len(departures)
        classification, basis, confidence = "insufficient_evidence", "observed_movement_flow", 20
        absolute_change = percentage_change = None
        if len(observations) >= 2:
            first, last = observations[0], observations[-1]
            absolute_change = last["researchHeadcount"] - first["researchHeadcount"]
            percentage_change = (absolute_change / first["researchHeadcount"]) if first["researchHeadcount"] else None
            classification = "increasing" if absolute_change > 0 else "decreasing" if absolute_change < 0 else "stable"
            basis, confidence = "reported_headcount", 95 if first["source"] != last["source"] else 90
        elif net >= 2:
            classification, confidence = "likely_increasing", min(80, 50 + net * 5)
        elif net <= -2:
            classification, confidence = "likely_decreasing", min(80, 50 + abs(net) * 5)
        elif len(arrivals) + len(departures) >= 3 and abs(net) <= 1:
            classification, confidence = "likely_stable", 55
        results.append({
            "organization": display_names[key], "classification": classification, "basis": basis,
            "confidence": confidence, "reportedHeadcountChange": absolute_change,
            "reportedHeadcountChangePct": round(percentage_change, 4) if percentage_change is not None else None,
            "observedResearchArrivals": len(arrivals), "observedResearchDepartures": len(departures),
            "observedNetFlow": net, "movementIds": sorted(set(arrivals + departures)),
            "headcountObservations": observations,
        })
    order = {"increasing": 0, "likely_increasing": 1, "decreasing": 2, "likely_decreasing": 3, "stable": 4, "likely_stable": 5, "insufficient_evidence": 6}
    return sorted(results, key=lambda x: (order[x["classification"]], -x["confidence"], x["organization"]))


def write_output(payload: dict[str, Any], output: str) -> str:
    if output.startswith("s3://"):
        process = subprocess.Popen(["aws", "s3", "cp", "-", output, "--only-show-errors"], stdin=subprocess.PIPE, text=True, encoding="utf-8")
        assert process.stdin is not None
        json.dump(payload, process.stdin, ensure_ascii=False, indent=2)
        process.stdin.write("\n"); process.stdin.close()
        if process.wait():
            raise RuntimeError("AWS CLI upload failed")
    else:
        Path(output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def feed_arg(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("feed must be NAME=URL")
    name, url = value.split("=", 1)
    if not name.strip() or not url.startswith(("http://", "https://")):
        raise argparse.ArgumentTypeError("feed must be NAME=http(s)://URL")
    return name.strip(), url


def main() -> int:
    parser = argparse.ArgumentParser(description="Track evidence-backed biotech employee and researcher movements.")
    parser.add_argument("period", choices=("day", "month"))
    parser.add_argument("date", type=parse_date, help="YYYY-MM-DD for day or YYYY-MM for month")
    parser.add_argument("--feed", action="append", type=feed_arg, metavar="NAME=URL", help="RSS/Atom feed; repeatable")
    parser.add_argument("--no-default-feeds", action="store_true")
    parser.add_argument("--input-jsonl", action="append", type=Path, default=[], help="licensed, manual, or internal evidence records")
    parser.add_argument("--no-historical-search", action="store_true", help="disable month-bounded Google News RSS searches")
    parser.add_argument("--output", help="local path or s3:// URI (default: project S3 prefix)")
    parser.add_argument("--cluster-window-days", type=int, default=180)
    parser.add_argument("--cluster-minimum", type=int, default=2)
    args = parser.parse_args()
    start, end = period_bounds(args.period, args.date)
    records: list[dict[str, Any]] = []
    errors = []
    source_runs = []
    feeds = {} if args.no_default_feeds else dict(DEFAULT_FEEDS)
    feeds.update(dict(args.feed or []))
    for source, url in feeds.items():
        try:
            rows = parse_feed(request(url), source); records.extend(rows)
            source_runs.append({"source": source, "mode": "current_feed", "recordCount": len(rows), "status": "ok"})
        except Exception as exc:
            errors.append({"source": source, "url": url, "error": str(exc)})
            source_runs.append({"source": source, "mode": "current_feed", "recordCount": 0, "status": "error"})
    if args.period == "month" and not args.no_historical_search:
        rows, search_errors = historical_news(start, end)
        records.extend(rows); errors.extend(search_errors)
        source_runs.append({"source": "Google News", "mode": "bounded_historical_search", "recordCount": len(rows), "status": "ok" if not search_errors else "partial" if rows else "error"})
    try:
        for path in args.input_jsonl:
            rows = load_jsonl(path); records.extend(rows)
            source_runs.append({"source": str(path), "mode": "historical_input", "recordCount": len(rows), "status": "ok"})
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 1
    in_period = []
    for record in records:
        stamp = parse_datetime(record.get("publishedAt") or record.get("date") or record.get("eventDate"))
        if stamp is None or start <= stamp.date() <= end:
            item = extract(record)
            if item:
                in_period.append(item)
    movements = merge_movements(in_period)
    trends = workforce_trends(movements, records)
    coverage = "failed" if not records else "complete" if source_runs and all(run["status"] == "ok" for run in source_runs) else "partial"
    payload = {
        "schemaVersion": 1, "period": args.period, "startDate": str(start), "endDate": str(end),
        "generatedAt": datetime.now(timezone.utc).isoformat(), "recordCount": len(records),
        "coverageStatus": coverage, "sourceRuns": source_runs,
        "movementCount": len(movements), "movements": movements,
        "workforceTrendCount": len(trends), "workforceTrends": trends,
        "clusters": clusters(movements, args.cluster_window_days, args.cluster_minimum), "sourceErrors": errors,
        "methodology": {"note": "Rule-based candidate extraction. Confidence is evidence completeness, not factual certainty; review evidence before investment use.", "workforceTrend": "Two reported R&D headcounts establish increasing/decreasing/stable. Without them, likely_* requires at least two net observed R&D movements; hiring intent is not reported headcount.", "linkedin": "Use a licensed export/API as --input-jsonl; this collector does not scrape LinkedIn.", "undatedRecords": "Included because supplied evidence may omit publication dates."},
    }
    key = f"people_movements_{args.period}_{start}_{end}.json"
    destination = args.output or S3_PREFIX + key
    try:
        write_output(payload, destination)
    except (OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 1
    print(f"Wrote {len(movements)} movements, {len(trends)} workforce trends, and {len(payload['clusters'])} clusters to {destination}")
    print(f"Coverage: {coverage}; fetched {len(records)} candidate records from {len(source_runs)} source runs")
    if errors:
        print(f"warning: {len(errors)} source(s) failed; details are in sourceErrors", file=sys.stderr)
    if coverage == "failed":
        print("error: no source returned records; output is not evidence of zero movements", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
