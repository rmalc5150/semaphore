#!/usr/bin/env python3
"""Collect public biotech and life-science conference records into S3 as JSON.

The collector uses Crossref's public scholarly metadata API because it exposes
stable DOI records from the societies' proceedings publishers.  A record is
included when its publication, presentation/event, or explicit acceptance date
falls in the requested period.  Crossref does not always expose the full
abstract or an author-notification date; unavailable values remain null.

Examples:
    python conference_materials.py day 2026-08-10
    python conference_materials.py month 2026-07 --region eu --region uk
    python conference_materials.py month 2026-07 --conference esmo --conference aacr
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from clinicaltrials_studies import parse_date, period_bounds


CROSSREF_URL = "https://api.crossref.org/works"
S3_PREFIX = "s3://processed-059416028963-us-east-1-an/conferences/"
USER_AGENT = "biotech-conference-collector/2.0 (mailto:data@example.com)"
PAGE_SIZE = 250


def conference(
    name: str,
    region: str,
    query: str,
    official_url: str,
    patterns: tuple[str, ...],
    *,
    prefix: str | None = None,
    doi_patterns: tuple[str, ...] = (),
    fields: tuple[str, ...] = ("biotechnology", "life sciences"),
) -> dict[str, Any]:
    return {
        "name": name,
        "region": region,
        "query": query,
        "prefix": prefix,
        "officialUrl": official_url,
        "doiPatterns": doi_patterns,
        "meetingPatterns": patterns,
        "fields": fields,
    }


# Curated major public meetings. "All" cannot literally include private,
# invitation-only, newly launched, or unannounced events; adding a conference is
# intentionally a single catalog entry. Regions describe the event location,
# not the organizer's headquarters.
CONFERENCES: dict[str, dict[str, Any]] = {
    "asco": {
        "name": "American Society of Clinical Oncology",
        "region": "us",
        "query": "ASCO Annual Meeting",
        "prefix": "10.1200",
        "officialUrl": "https://meetings.asco.org/abstracts-presentations",
        "doiPatterns": (r"^10\.1200/jco\..*_suppl\.",),
        "meetingPatterns": (r"asco", r"annual meeting", r"suppl"),
        "fields": ("oncology", "clinical research", "biotechnology"),
    },
    "esmo": {
        "name": "European Society for Medical Oncology",
        "region": "eu",
        "query": "ESMO Congress",
        "prefix": "10.1016",
        "officialUrl": "https://oncologypro.esmo.org/meeting-resources",
        "doiPatterns": (r"^10\.1016/j\.annonc\.",),
        "meetingPatterns": (r"esmo", r"congress", r"abstract"),
        "fields": ("oncology", "clinical research", "biotechnology"),
    },
    "aacr": {
        "name": "American Association for Cancer Research",
        "region": "us",
        "query": "AACR Annual Meeting",
        "prefix": "10.1158",
        "officialUrl": "https://aacrjournals.org/pages/meeting-abs",
        "doiPatterns": (r"^10\.1158/1538-7445\.am20\d\d-",),
        "meetingPatterns": (r"aacr", r"annual meeting", r"proceedings"),
        "fields": ("cancer research", "drug discovery", "biotechnology"),
    },
    # United States
    "bio-international": conference("BIO International Convention", "us", "BIO International Convention", "https://convention.bio.org/", (r"bio international", r"convention", r"biotech")),
    "ash": conference("American Society of Hematology Annual Meeting", "us", "ASH Annual Meeting hematology", "https://www.hematology.org/meetings/annual-meeting", (r"ash", r"annual meeting", r"hematology"), fields=("hematology", "cell therapy", "clinical research")),
    "sitc": conference("SITC Annual Meeting", "us", "SITC Annual Meeting", "https://www.sitcancer.org/annualmeeting", (r"sitc", r"annual meeting", r"immunotherapy"), fields=("immunotherapy", "oncology", "biotechnology")),
    "slas": conference("SLAS International Conference and Exhibition", "us", "SLAS International Conference", "https://www.slas.org/events-calendar/", (r"slas", r"international conference", r"laboratory automation"), fields=("drug discovery", "laboratory automation", "life sciences")),
    "synbiobeta": conference("SynBioBeta Global Conference", "us", "SynBioBeta Global Conference", "https://www.synbiobeta.com/conference", (r"synbiobeta", r"global conference", r"synthetic biology"), fields=("synthetic biology", "biotechnology")),
    "festival-genomics-us": conference("Festival of Genomics & Biodata USA", "us", "Festival of Genomics Biodata USA", "https://festivalofgenomics.com/", (r"festival of genomics", r"biodata", r"usa"), fields=("genomics", "bioinformatics", "precision medicine")),
    "jpm-healthcare": conference("J.P. Morgan Healthcare Conference", "us", "J.P. Morgan Healthcare Conference", "https://www.jpmorgan.com/about-us/events-conferences/health-care-conference", (r"j\.?p\.? morgan", r"healthcare conference", r"biopharma"), fields=("biopharma", "healthcare investment", "biotechnology")),
    "hlth": conference("HLTH", "us", "HLTH conference healthcare", "https://www.hlth.com/", (r"hlth", r"conference", r"healthcare"), fields=("digital health", "healthcare", "biotechnology")),
    # European Union
    "bio-europe": conference("BIO-Europe", "eu", "BIO-Europe biotechnology", "https://informaconnect.com/bioeurope/", (r"bio-europe", r"partnering", r"biotech")),
    "bio-europe-spring": conference("BIO-Europe Spring", "eu", "BIO-Europe Spring biotechnology", "https://informaconnect.com/bioeurope-spring/", (r"bio-europe spring", r"partnering", r"biotech")),
    "eha": conference("European Hematology Association Congress", "eu", "EHA Congress hematology", "https://ehaweb.org/connect-network/congress", (r"eha", r"congress", r"hematology"), fields=("hematology", "cell therapy", "clinical research")),
    "escmid-global": conference("ESCMID Global", "eu", "ESCMID Global congress", "https://www.escmid.org/congress-events/escmid-global/", (r"escmid", r"global", r"microbiology|infectious"), fields=("microbiology", "infectious diseases", "diagnostics")),
    "esact": conference("ESACT Meeting", "eu", "ESACT meeting animal cell technology", "https://esact.org/meetings/", (r"esact", r"meeting", r"animal cell technology"), fields=("bioprocessing", "cell technology", "biotechnology")),
    "biospain": conference("BIOSPAIN", "eu", "BIOSPAIN biotechnology conference", "https://www.asebio.com/en/events/biospain", (r"biospain", r"conference|congress", r"biotech")),
    "nordic-life-science-days": conference("Nordic Life Science Days", "eu", "Nordic Life Science Days", "https://www.nlsdays.com/", (r"nordic life science days", r"nls days", r"partnering")),
    # United Kingdom (kept separate from EU for regional filtering)
    "biotrinity": conference("BioTrinity", "uk", "BioTrinity life sciences conference", "https://biotrinity.com/", (r"biotrinity", r"life sciences", r"conference")),
    "genesis": conference("Genesis Conference", "uk", "Genesis Conference life science", "https://www.genesisconference.com/", (r"genesis", r"life science", r"conference")),
    "london-biotech-show": conference("London Biotechnology Show", "uk", "London Biotechnology Show", "https://londonbiotechnologyshow.com/", (r"london biotechnology show", r"biotech", r"conference|exhibition")),
    "elrig-drug-discovery": conference("ELRIG Drug Discovery", "uk", "ELRIG Drug Discovery conference", "https://elrig.org/portfolio/drug-discovery/", (r"elrig", r"drug discovery", r"conference"), fields=("drug discovery", "laboratory science", "biotechnology")),
    "festival-genomics-uk": conference("Festival of Genomics & Biodata London", "uk", "Festival of Genomics Biodata London", "https://festivalofgenomics.com/london/en/page/home", (r"festival of genomics", r"biodata", r"london"), fields=("genomics", "bioinformatics", "precision medicine")),
    "oncology-professional-care": conference("Oncology Professional Care", "uk", "Oncology Professional Care conference", "https://www.oncologyprofessionalcare.co.uk/", (r"oncology professional care", r"conference", r"oncology"), fields=("oncology", "clinical care", "biotechnology")),
    # Asia
    "biojapan": conference("BioJapan", "asia", "BioJapan biotechnology", "https://jcd-expo.jp/en/", (r"biojapan", r"biotechnology", r"partnering")),
    "bio-asia-taiwan": conference("BIO Asia-Taiwan", "asia", "BIO Asia Taiwan biotechnology", "https://bioasiataiwan.com/en", (r"bio asia", r"taiwan", r"biotech")),
    "bio-korea": conference("BIO KOREA", "asia", "BIO KOREA conference", "https://www.biokorea.org/", (r"bio korea", r"conference", r"biotech")),
    "china-bio": conference("ChinaBio Partnering Forum", "asia", "ChinaBio Partnering Forum", "https://informaconnect.com/chinabio-partnering/", (r"chinabio", r"partnering", r"biotech")),
    "bangalore-india-bio": conference("Bengaluru Tech Summit - Biotech", "asia", "Bengaluru Tech Summit biotechnology", "https://bengalurutechsummit.com/", (r"bengaluru|bangalore", r"tech summit", r"biotech")),
    "biologics-manufacturing-asia": conference("Biologics Manufacturing Asia", "asia", "Biologics Manufacturing Asia", "https://www.imapac.com/events/biologics-manufacturing-asia", (r"biologics manufacturing", r"asia", r"conference"), fields=("biomanufacturing", "biologics", "biotechnology")),
    "esmo-asia": conference("ESMO Asia Congress", "asia", "ESMO Asia Congress", "https://www.esmo.org/meeting-calendar/esmo-asia", (r"esmo", r"asia", r"congress"), prefix="10.1016", doi_patterns=(r"^10\.1016/j\.annonc\.",), fields=("oncology", "clinical research", "biotechnology")),
    "asco-breakthrough": conference("ASCO Breakthrough", "asia", "ASCO Breakthrough meeting", "https://www.asco.org/meetings-education/meetings", (r"asco", r"breakthrough", r"meeting"), prefix="10.1200", fields=("oncology", "clinical research", "biotechnology")),
}

REGIONS = ("asia", "eu", "uk", "us")


def request_json(url: str, params: dict[str, str], retries: int = 4) -> dict[str, Any]:
    request = Request(
        f"{url}?{urlencode(params)}",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=90) as response:
                result = json.load(response)
            if not isinstance(result, dict):
                raise RuntimeError("Crossref returned an unexpected response")
            return result
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"Crossref returned HTTP {exc.code}: {detail[:500]}") from exc
        except (URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"could not contact Crossref: {exc}") from exc
            time.sleep(2**attempt)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Crossref returned invalid JSON") from exc
    raise AssertionError("unreachable")


def date_from_parts(value: Any) -> date | None:
    """Read Crossref's {date-parts:[[Y,M,D]]} format without inventing a day."""
    if not isinstance(value, dict):
        return None
    parts = value.get("date-parts")
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
        return None
    first = parts[0]
    if len(first) < 3:  # Month/year precision is not an exact event date.
        return None
    try:
        return date(int(first[0]), int(first[1]), int(first[2]))
    except (TypeError, ValueError):
        return None


def first_date(record: dict[str, Any], fields: Iterable[str]) -> date | None:
    for field in fields:
        parsed = date_from_parts(record.get(field))
        if parsed is not None:
            return parsed
    return None


def assertion_date(record: dict[str, Any], name: str) -> date | None:
    for assertion in record.get("assertion", []):
        if not isinstance(assertion, dict) or str(assertion.get("name", "")).lower() != name:
            continue
        value = assertion.get("value")
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                continue
    return None


def strip_markup(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(text)).strip() or None


def list_strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def is_conference_record(record: dict[str, Any], config: dict[str, Any]) -> bool:
    doi = str(record.get("DOI", "")).lower()
    if any(re.search(pattern, doi, re.I) for pattern in config["doiPatterns"]):
        return True
    event = record.get("event") if isinstance(record.get("event"), dict) else {}
    event_name = event.get("name")
    haystack = " ".join(
        ([str(event_name)] if event_name else [])
        + list_strings(record.get("container-title"))
        + list_strings(record.get("subtitle"))
        + [str(record.get("publisher", "")), str(record.get("issue", ""))]
    )
    # A society name alone is insufficient: publishers also deposit guidelines,
    # editorials, podcasts, and news under the same DOI prefix.
    matches = sum(bool(re.search(pattern, haystack, re.I)) for pattern in config["meetingPatterns"])
    return matches >= 2


def infer_presentation_type(record: dict[str, Any], title: str | None) -> str | None:
    text = " ".join(
        [title or "", str(record.get("article-number", "")), str(record.get("subtype", ""))]
        + list_strings(record.get("subtitle"))
    )
    patterns = (
        (r"\b(e-?poster|poster)\b", "Poster"),
        (r"\b(mini[ -]?oral|mo)\b", "Mini Oral"),
        (r"\b(oral|proffered paper|presidential symposium)\b", "Oral"),
        (r"\b(publication only)\b", "Publication Only"),
    )
    for pattern, label in patterns:
        if re.search(pattern, text, re.I):
            return label
    return None


def normalize_record(record: dict[str, Any], conference: str) -> dict[str, Any]:
    config = CONFERENCES[conference]
    title_values = list_strings(record.get("title"))
    title = strip_markup(title_values[0]) if title_values else None
    event = record.get("event") if isinstance(record.get("event"), dict) else {}
    publication_date = first_date(
        record, ("published-online", "published-print", "published", "issued")
    )
    presentation_date = first_date(event, ("start",)) or first_date(
        record, ("event-date",)
    )
    acceptance_date = first_date(record, ("accepted",)) or assertion_date(record, "accepted")
    authors = []
    for author in record.get("author", []):
        if not isinstance(author, dict):
            continue
        authors.append(
            {
                "given": author.get("given"),
                "family": author.get("family"),
                "orcid": author.get("ORCID"),
                "affiliations": [
                    item.get("name")
                    for item in author.get("affiliation", [])
                    if isinstance(item, dict) and item.get("name")
                ],
            }
        )
    doi = record.get("DOI")
    return {
        "conferenceId": conference,
        "conference": config["name"],
        "region": config["region"],
        "title": title,
        "abstract": strip_markup(record.get("abstract")),
        "authors": authors,
        "doi": doi,
        "url": record.get("URL") or (f"https://doi.org/{doi}" if doi else None),
        "meetingName": event.get("name"),
        "presentationType": infer_presentation_type(record, title),
        "presentationDate": presentation_date.isoformat() if presentation_date else None,
        "acceptanceDate": acceptance_date.isoformat() if acceptance_date else None,
        "publicationDate": publication_date.isoformat() if publication_date else None,
        "abstractNumber": record.get("article-number"),
        "containerTitle": (list_strings(record.get("container-title")) or [None])[0],
        "volume": record.get("volume"),
        "issue": record.get("issue"),
        "page": record.get("page"),
        "sourceMetadata": record,
    }


def record_in_period(item: dict[str, Any], start: date, end: date) -> bool:
    for field in ("acceptanceDate", "presentationDate", "publicationDate"):
        value = item.get(field)
        if isinstance(value, str):
            try:
                if start <= date.fromisoformat(value) <= end:
                    return True
            except ValueError:
                pass
    return False


def fetch_conference(conference: str, start: date, end: date) -> list[dict[str, Any]]:
    config = CONFERENCES[conference]
    # Acceptance can precede proceedings publication by many months.  The API
    # query is widened, then records are filtered using all available dates.
    query_start = start - timedelta(days=370)
    query_end = end + timedelta(days=370)
    cursor = "*"
    found: dict[str, dict[str, Any]] = {}
    pages = 0
    while cursor and pages < 40:
        filters = [f"from-pub-date:{query_start}", f"until-pub-date:{query_end}"]
        if config.get("prefix"):
            filters.insert(0, f"prefix:{config['prefix']}")
        payload = request_json(
            CROSSREF_URL,
            {
                "query.bibliographic": config["query"],
                "filter": ",".join(filters),
                "rows": str(PAGE_SIZE),
                "cursor": cursor,
            },
        )
        message = payload.get("message", {})
        records = message.get("items", []) if isinstance(message, dict) else []
        if not isinstance(records, list):
            raise RuntimeError("Crossref response has no valid items list")
        for record in records:
            if not isinstance(record, dict) or not is_conference_record(record, config):
                continue
            item = normalize_record(record, conference)
            if record_in_period(item, start, end):
                identity = str(item.get("doi") or item.get("url") or item.get("title"))
                found[identity] = item
        pages += 1
        next_cursor = message.get("next-cursor") if isinstance(message, dict) else None
        if not records or not isinstance(next_cursor, str) or next_cursor == cursor:
            break
        cursor = next_cursor
    return sorted(
        found.values(),
        key=lambda item: (
            item.get("presentationDate") or item.get("publicationDate") or "",
            item.get("title") or "",
        ),
    )


def build_payload(conference: str, period: str, start: date, end: date) -> dict[str, Any]:
    records = fetch_conference(conference, start, end)
    # Every proceedings record represents an abstract even when its full text
    # was not deposited in Crossref; the abstract field then remains null.
    abstracts = records
    presentations = [
        {
            "title": item["title"],
            "doi": item["doi"],
            "url": item["url"],
            "meetingName": item["meetingName"],
            "presentationType": item["presentationType"],
            "presentationDate": item["presentationDate"],
            "abstractNumber": item["abstractNumber"],
        }
        for item in records
    ]
    acceptances = [
        {
            "title": item["title"],
            "doi": item["doi"],
            "acceptanceDate": item["acceptanceDate"],
        }
        for item in records
        if item.get("acceptanceDate") is not None
    ]
    config = CONFERENCES[conference]
    return {
        "conferenceId": conference,
        "conference": config["name"],
        "organization": config["name"],
        "region": config["region"],
        "fields": list(config["fields"]),
        "period": period,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "collectedAt": datetime.now(timezone.utc).isoformat(),
        "sources": {"official": config["officialUrl"], "metadata": CROSSREF_URL},
        "coverageNote": (
            "Only public proceedings metadata is included. Abstract text, presentation type/date, "
            "and acceptance date are null when the publisher does not deposit those fields. "
            "An acceptance date is never inferred from a publication date."
        ),
        "recordCount": len(records),
        "abstractCount": len(abstracts),
        "presentationCount": len(presentations),
        "acceptanceDateCount": len(acceptances),
        "abstracts": abstracts,
        "presentations": presentations,
        "acceptanceDates": acceptances,
        "records": records,
    }


def upload_to_s3(payload: dict[str, Any], destination: str) -> None:
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
    if process.wait():
        raise RuntimeError("AWS CLI upload failed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect public biotech and life-science conference data by region."
    )
    parser.add_argument("period", choices=("day", "month"), nargs="?")
    parser.add_argument("date", type=parse_date, nargs="?", help="YYYY-MM-DD (or YYYY-MM for month)")
    parser.add_argument("--conference", choices=CONFERENCES, action="append")
    parser.add_argument("--region", choices=REGIONS, action="append")
    parser.add_argument(
        "--list-conferences", action="store_true", help="list catalog IDs and exit"
    )
    parser.add_argument("--s3-prefix", default=S3_PREFIX)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_conferences:
        for conference_id, config in CONFERENCES.items():
            print(f"{conference_id}\t{config['region']}\t{config['name']}")
        return 0
    if args.period is None or args.date is None:
        print("error: period and date are required unless --list-conferences is used", file=sys.stderr)
        return 2
    start, end = period_bounds(args.period, args.date)
    if args.conference:
        conferences = args.conference
        if args.region:
            conferences = [
                item for item in conferences if CONFERENCES[item]["region"] in args.region
            ]
    elif args.region:
        conferences = [
            item for item, config in CONFERENCES.items() if config["region"] in args.region
        ]
    else:
        conferences = list(CONFERENCES)
    failures: list[str] = []
    for conference in conferences:
        try:
            payload = build_payload(conference, args.period, start, end)
            key = f"{conference}/conference_{conference}_{args.period}_{start}_{end}.json"
            destination = args.s3_prefix.rstrip("/") + "/" + key
            upload_to_s3(payload, destination)
            print(
                f"Uploaded {payload['recordCount']:,} {CONFERENCES[conference]['name']} "
                f"records to {destination}"
            )
        except RuntimeError as exc:
            print(f"error [{conference}]: {exc}", file=sys.stderr)
            failures.append(conference)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
