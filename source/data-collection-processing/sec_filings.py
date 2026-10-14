#!/usr/bin/env python3
"""SEC metadata collection with pinned snapshots and shared persistence.

New commands: historical START END (exclusive), daily [DATE]. Legacy day/month
commands retain their existing envelope for disclosure consumers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date, datetime, time as daytime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from collection_storage import (AlreadyComplete, CollectionRun, Conflict, StorageSettings,
    advance_watermark, now, read_watermark, task_spec, write_checked, write_json)
from research_contract import ROOT, COLLECTION_UNIVERSE, load_json, parse_instant, seal_record

VERSION = "sec-index-1.2"
SOURCE, DATASET = "sec_edgar", "filings"
NY = ZoneInfo("America/New_York")
HEADER = "CIK|Company Name|Form Type|Date Filed|Filename"
PATH_RE = re.compile(r"^edgar/data/[0-9]+/(?:[0-9]{18}/)?([0-9]{10}-[0-9]{2}-[0-9]{6})\.txt$")
MAX_INDEX_BYTES = 128 * 1024 * 1024


class SourceError(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def normalize_cik(value):
    value = str(value).strip()
    if not re.fullmatch(r"[0-9]{1,10}", value) or int(value) == 0:
        raise ValueError("CIK must contain 1–10 digits and be nonzero")
    return value.zfill(10)


def quarter_of(day):
    return day.year, (day.month - 1) // 3 + 1


def index_url(year, quarter):
    return f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/master.idx"


def normalize_name(value):
    words = re.sub(r"[\W_]+", " ", unicodedata.normalize("NFKC", value).casefold()).split()
    while words and words[-1] in {"inc", "incorporated", "corp", "corporation", "ltd", "limited", "plc", "se", "ag", "co", "company"}:
        words.pop()
    return " ".join(words)


class SECClient:
    """Paced requests, bounded retry, and no fabricated operator identity."""
    def __init__(self, user_agent, opener=urlopen, sleeper=time.sleep, monotonic=time.monotonic,
                 interval=0.25, attempts=4):
        if not isinstance(user_agent, str) or "\n" in user_agent or "\r" in user_agent:
            raise ValueError("SEC_USER_AGENT must contain organization and contact email")
        email = re.search(r"[^\s@]+@([^\s@]+\.[^\s@]+)", user_agent)
        if not email or email.start() == 0 or email.group(1).lower() in {"example.com", "example.org", "example.net"}:
            raise ValueError("configure SEC_USER_AGENT with a real organization and contact email")
        self.agent, self.opener, self.sleep, self.monotonic = user_agent, opener, sleeper, monotonic
        self.interval, self.attempts, self.last_request = interval, attempts, None

    def fetch(self, year, quarter):
        for attempt in range(self.attempts):
            if self.last_request is not None:
                self.sleep(max(0, self.interval - (self.monotonic() - self.last_request)))
            self.last_request = self.monotonic()
            try:
                request = Request(index_url(year, quarter), headers={"User-Agent": self.agent,
                    "Accept": "text/plain", "Accept-Encoding": "identity"})
                with self.opener(request, timeout=90) as response:
                    raw = response.read(MAX_INDEX_BYTES + 1)
                    declared = response.headers.get("Content-Length")
                if len(raw) > MAX_INDEX_BYTES:
                    raise SourceError("index_too_large")
                if declared is not None and int(declared) != len(raw):
                    raise SourceError("truncated_index")
                return raw
            except HTTPError as exc:
                if exc.code == 404:
                    raise SourceError("index_unavailable") from exc
                if exc.code not in {429, 500, 502, 503, 504}:
                    raise SourceError("sec_http_error") from exc
                if attempt == self.attempts - 1:
                    raise SourceError("sec_retries_exhausted") from exc
                retry = exc.headers.get("Retry-After") if exc.headers else None
                delay = 2 ** attempt
                if retry:
                    try:
                        delay = max(delay, float(retry))
                    except ValueError:
                        try:
                            delay = max(delay, (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds())
                        except (ValueError, TypeError):
                            pass
                if delay > 120:
                    raise SourceError("sec_retry_deferred") from exc
                self.sleep(delay)
            except (URLError, TimeoutError) as exc:
                if attempt == self.attempts - 1:
                    raise SourceError("sec_retries_exhausted") from exc
                self.sleep(2 ** attempt)
        raise AssertionError("unreachable")


def parse_index(raw, year, quarter, consume=None):
    """Fail on malformed rows, rather than silently dropping filings."""
    # SEC indexes can end directly after the final filename. Validate that
    # row below; a missing newline alone is not evidence of truncation.
    lines = raw.decode("latin-1").splitlines()
    try:
        header_at = next(i for i, line in enumerate(lines) if line.strip() == HEADER)
    except StopIteration as exc:
        raise SourceError("index_header_missing") from exc
    received = None
    for line in lines[:header_at]:
        if line.lower().startswith("last data received:"):
            value = line.split(":", 1)[1].strip()
            for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    received = datetime.strptime(value, fmt).date()
                    break
                except ValueError:
                    pass
            if received is None:
                raise SourceError("index_coverage_date_invalid")
    if received is None:
        raise SourceError("index_coverage_date_missing")
    rows, seen = [], set()
    for number, line in enumerate(lines[header_at + 1:], header_at + 2):
        if not line.strip() or set(line.strip()) == {"-"}:
            continue
        parts = line.split("|")
        if len(parts) != 5:
            raise SourceError("index_row_malformed")
        cik, company, form, filed, filename = (part.strip() for part in parts)
        try:
            cik = normalize_cik(cik)
            filed_date = date.fromisoformat(filed)
        except ValueError as exc:
            raise SourceError("index_row_malformed") from exc
        match = PATH_RE.fullmatch(filename)
        if not company or not form or not match or quarter_of(filed_date) != (year, quarter) or filed_date > received:
            raise SourceError("index_row_malformed")
        identity = (cik, company, form, filed, filename)
        # Publication validates the entire index but need not retain its rows.
        # Compact identities keep that path bounded by hashes, not full strings.
        seen_identity = hashlib.sha256(repr(identity).encode()).digest() if consume else identity
        if seen_identity in seen:
            continue
        seen.add(seen_identity)
        row = {"cik": cik, "company_name": company, "form": form, "filing_date": filed,
               "filename": filename, "accession_number": match.group(1), "index_line": number}
        if consume:
            consume(row)
        else:
            rows.append(row)
    return rows, received


def assert_coverage(received, start, end):
    # Known weekend gaps are empty; unknown weekday gaps remain partial.
    day = max(start, received + timedelta(days=1))
    while day < end:
        if day.weekday() < 5:
            raise SourceError("index_coverage_incomplete")
        day += timedelta(days=1)


class CompanyMatcher:
    def __init__(self, universe, company_ids=(), sectors=()):
        known = {c["company_id"] for c in universe["companies"]}
        if set(company_ids) - known:
            raise ValueError("unknown --company-id")
        self.companies = {c["company_id"]: c for c in universe["companies"] if c["collection_enabled"] and c["review_status"] != "rejected"
            and (not company_ids or c["company_id"] in company_ids)
            and (not sectors or any(s["sector_id"] in sectors and s["review_status"] != "rejected" for s in c["sectors"]))}
        self.ciks, self.names = {}, {}
        for cid, company in self.companies.items():
            name = normalize_name(company["canonical_name"])
            if name:
                self.names.setdefault(name, set()).add(cid)
        for alias in universe["company_aliases"]:
            if alias["company_id"] in self.companies and alias["review_status"] != "rejected":
                name = normalize_name(alias["alias"])
                if name:
                    self.names.setdefault(name, set()).add(alias["company_id"])
        for identifier in universe["external_identifiers"]:
            if identifier["system"] in {"sec_cik", "cik"} and identifier["entity_id"] in self.companies and identifier["review_status"] == "verified":
                self.ciks.setdefault(normalize_cik(identifier["value"]), set()).add(identifier["entity_id"])

    def match(self, row):
        # CIKs are not recycled. This identifies entities, not historical sector
        # membership, ownership, or feature eligibility.
        ciks = self.ciks.get(row["cik"], set())
        confirmed = {cid for cid in ciks if self.companies[cid]["review_status"] == "verified"
                     and self.companies[cid]["entity_type"] == "legal_entity"}
        if len(ciks) != 1:
            confirmed = set()
        candidates = (ciks | self.names.get(normalize_name(row["company_name"]), set())) - confirmed
        return confirmed, candidates


def select_filings(rows, start, end, matcher, selection="universe", ciks=(), forms=()):
    groups = {}
    for row in rows:
        if start <= date.fromisoformat(row["filing_date"]) < end:
            groups.setdefault(row["accession_number"], []).append(row)
    output = []
    for accession, issuers in groups.items():
        if len({r["filing_date"] for r in issuers}) != 1:
            raise SourceError("conflicting_accession_metadata")
        if forms and not set(forms).intersection(r['form'] for r in issuers):
            continue
        if ciks and not any(row["cik"] in ciks for row in issuers):
            continue
        confirmed, candidates, unresolved_ciks = set(), set(), set()
        for row in issuers:
            matched, proposed = matcher.match(row)
            confirmed.update(matched)
            candidates.update(proposed)
            if not matched:
                unresolved_ciks.add(row["cik"])
        candidates -= confirmed
        if selection == "universe" and not confirmed and not candidates:
            continue
        output.append({"accession_number": accession, "issuer_rows": sorted(issuers, key=lambda r: (r["cik"], r["filename"])),
                       "company_ids": sorted(confirmed), "candidate_company_ids": sorted(candidates),
                       "unresolved_ciks": sorted(unresolved_ciks)})
    return sorted(output, key=lambda r: (r["issuer_rows"][0]["filing_date"], r["accession_number"]))


def normalized_record(filing, run, snapshot):
    issuer_rows = filing["issuer_rows"]
    confirmed, candidates = filing["company_ids"], filing["candidate_company_ids"]
    payload = {"accession_number": filing["accession_number"], "form": issuer_rows[0]["form"],
        "filing_date": issuer_rows[0]["filing_date"],
        "issuer_rows": [{k: v for k, v in row.items() if k not in {"index_line", "accession_number"}} for row in issuer_rows],
        "document_urls": sorted({"https://www.sec.gov/Archives/" + row["filename"] for row in issuer_rows}),
        "candidate_company_ids": candidates, "unresolved_ciks": filing["unresolved_ciks"],
        "company_match_basis": "verified_sec_cik" if confirmed else "unresolved",
        "candidate_match_basis": "unverified_cik_or_name" if candidates else None}
    index_forms = sorted({row['form'] for row in issuer_rows})
    if len(index_forms) > 1:
        # The index can list one accession under multiple form types. Preserve
        # all labels and issuer evidence; do not invent a canonical primary form.
        payload.update(form=' / '.join(index_forms), index_forms=index_forms)
    return seal_record({"document_type": "collected_record", "schema_version": "1.0", "source": SOURCE,
        "dataset": DATASET, "source_record_id": filing["accession_number"], "source_record_id_basis": "provider",
        "source_url": payload["document_urls"][0], "universe_version": run.universe["universe_version"],
        "company_ids": confirmed, "listing_ids": [], "product_ids": [], "person_ids": [],
        "entity_match_status": "partial" if confirmed and (candidates or filing["unresolved_ciks"]) else "matched" if confirmed else "unresolved",
        "event_at": {"value": payload["filing_date"], "precision": "day", "source_timezone": "America/New_York"},
        "available_at": None, "source_updated_at": None, "ingested_at": snapshot["retrieved_at"],
        "availability_basis": "unknown", "availability_evidence": [], "run_id": run.run_id, "payload": payload})


def source_snapshot(run, client, year, quarter, cache):
    prefix = run.state["manifest_prefix"]
    snapshot = None
    # With no committed page, a newer index can resolve yesterday's coverage
    # delay. Once pages exist, offset-based resume must retain the pinned input.
    ancestor = run.state["resumed_from_run_id"] if run.state["pages"] else None
    visited = set()
    while ancestor:
        if ancestor in visited:
            raise Conflict("source snapshot ancestry cycle")
        visited.add(ancestor)
        parent = prefix.rsplit("/", 1)[0] + "/" + ancestor
        saved = run.store.get(parent + "/input.json")
        if saved:
            snapshot = json.loads(saved.body)
            break
        started = run.store.get(parent + "/started.json")
        if started is None:
            raise Conflict("missing source snapshot ancestry")
        ancestor = json.loads(started.body)["resumed_from_run_id"]
    if snapshot is None and run.state["pages"]:
        raise Conflict("committed pages have no pinned source snapshot")
    if snapshot is None:
        if (year, quarter) not in cache:
            # Chronological backfills may span decades. Keep one quarter's
            # parsed rows, not every quarterly index seen in the invocation.
            cache.clear()
            raw = client.fetch(year, quarter)
            retrieved_at = now()
            rows, received = parse_index(raw, year, quarter)
            checksum = hashlib.sha256(raw).hexdigest()
            key = f"source_documents/sec_edgar/year={year}/quarter={quarter}/{checksum}.idx"
            write_checked(run.store, key, raw, content_type="text/plain")
            snapshot = {"source_url": index_url(year, quarter), "key": key, "sha256": checksum,
                "retrieved_at": retrieved_at, "last_data_received": received.isoformat(),
                "year": year, "quarter": quarter, "index_rows": len(rows)}
            cache[(year, quarter)] = (snapshot, rows)
        snapshot, rows = cache[(year, quarter)]
    else:
        obj = run.store.get(snapshot["key"])
        if obj is None or hashlib.sha256(obj.body).hexdigest() != snapshot["sha256"]:
            raise Conflict("pinned SEC index is missing or corrupt")
        rows, received = parse_index(obj.body, year, quarter)
        if snapshot["last_data_received"] != received.isoformat():
            raise Conflict("source snapshot metadata disagrees with bytes")
    write_json(run.store, prefix + "/input.json", snapshot)
    return snapshot, rows


def collect_window(store, settings, universe, taxonomy, client, start, end, mode,
                   scope, matcher, cache, refresh=False, page_size=500, max_records=None):
    spec = make_spec(start, end, mode, scope, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=not refresh, refresh=refresh)
    except AlreadyComplete as exc:
        return {"status": "complete", "already_complete": True, "manifest": str(exc), "task": spec}
    try:
        year, quarter = quarter_of(start)
        if quarter_of(end - timedelta(days=1)) != (year, quarter):
            raise ValueError("a collection window must stay within one quarter")
        snapshot, rows = source_snapshot(run, client, year, quarter, cache)
        assert_coverage(date.fromisoformat(snapshot["last_data_received"]), start, end)
        filings = select_filings(rows, start, end, matcher, scope["selection"], scope["ciks"], scope["forms"])
        position = int(run.cursor) if run.cursor is not None else (len(filings) if run.exhausted else 0)
        if not 0 <= position <= len(filings) or run.state["record_count"] != position:
            raise Conflict("cursor/count does not agree with the pinned index selection")
        allowance = len(filings) if max_records is None else min(len(filings), position + max_records)
        if not filings and not run.exhausted:
            run.commit_page([], exhausted=True)
        while position < allowance:
            following = min(position + page_size, allowance)
            records = (normalized_record(filing, run, snapshot) for filing in filings[position:following])
            run.commit_page(records, next_cursor=str(following) if following < len(filings) else None,
                            exhausted=following == len(filings))
            position = following
        if not run.exhausted:
            manifest = run.finish("partial", "record_limit", expected_records=len(filings))
            return {"status": "partial", "reason": "record_limit", "manifest": manifest, "task": spec}
        summary = {"selected_filings": len(filings), "confirmed_company_matches": sum(bool(f["company_ids"]) for f in filings),
            "candidate_only_filings": sum(not f["company_ids"] and bool(f["candidate_company_ids"]) for f in filings),
            "unmatched_filings": sum(not f["company_ids"] and not f["candidate_company_ids"] for f in filings)}
        sector_counts, observed_companies = {}, set()
        for filing in filings:
            company_ids = set(filing["company_ids"]) | set(filing["candidate_company_ids"])
            observed_companies.update(company_ids)
            sectors = {s["sector_id"] for cid in company_ids for s in matcher.companies[cid]["sectors"]
                       if s["review_status"] != "rejected"}
            for sector in sectors:
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
        summary["filings_by_configured_sector_including_candidates"] = sector_counts
        summary["companies_with_no_selected_filing"] = sorted(set(matcher.companies) - observed_companies)
        write_json(store, run.state["manifest_prefix"] + "/selection.json", summary)
        manifest = run.finish("complete", expected_records=len(filings))
        return {"status": "complete", "manifest": manifest, "task": spec, **summary}
    except SourceError as exc:
        status = "partial" if exc.code in {"index_coverage_incomplete", "index_unavailable", "sec_retry_deferred"} else "failed"
        return {"status": status, "reason": exc.code, "manifest": run.finish(status, exc.code), "task": spec}
    except Conflict:
        raise
    except Exception:
        if run.pending_final is None:
            run.finish("failed", "collection_error")
        raise


def midnight(day):
    return datetime.combine(day, daytime.min, NY).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def make_spec(start, end, mode, scope, universe, taxonomy):
    return task_spec(SOURCE, DATASET, mode, midnight(start), midnight(end), scope, VERSION, universe, taxonomy)


def windows(start, end, mode):
    while start < end:
        following = start + timedelta(days=1) if mode == "daily" else date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        following = min(following, end)
        yield start, following
        start = following


def arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("historical", "daily"))
    parser.add_argument("start", nargs="?", type=date.fromisoformat, help="historical start or explicit daily date")
    parser.add_argument("end", nargs="?", type=date.fromisoformat, help="historical exclusive end")
    parser.add_argument("--origin", type=date.fromisoformat, help="initial daily watermark origin")
    parser.add_argument("--overlap-days", type=int, default=3)
    parser.add_argument("--refresh", action="store_true", help="re-fetch completed/pinned windows")
    parser.add_argument("--selection", choices=("universe", "all"), default="universe")
    parser.add_argument("--company-id", action="append", default=[])
    parser.add_argument("--sector", action="append", choices=("biotech", "robotics", "semiconductors", "energy_storage"), default=[])
    parser.add_argument("--cik", action="append", type=normalize_cik, default=[])
    parser.add_argument("--form", action="append", default=[])
    parser.add_argument("--page-size", type=int, default=500)
    parser.add_argument("--max-records", type=int, help="per-window attempt limit; truncated runs remain partial")
    parser.add_argument("--universe", type=Path, default=COLLECTION_UNIVERSE)
    parser.add_argument("--taxonomy", type=Path, default=ROOT / "config/sectors.v1.json")
    parser.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.example.json")
    parser.add_argument("--backend", choices=("local", "s3"))
    parser.add_argument("--output-root")
    parser.add_argument("--s3-bucket")
    parser.add_argument("--s3-prefix")
    parser.add_argument("--region")
    parser.add_argument("--user-agent", default=os.getenv("SEC_USER_AGENT"))
    parser.add_argument("--index-file", type=Path, help="offline source fixture; local output only, separate task scope")
    from historical_policy import add_end_option, resolve_dates
    add_end_option(parser)
    args = parser.parse_args(argv)
    resolve_dates(parser, args, args.mode)
    if args.mode == "historical" and (args.start is None or args.end is None):
        parser.error("historical requires START END (end exclusive)")
    if args.mode == "daily" and args.end is not None:
        parser.error("daily accepts at most one explicit date")
    if args.overlap_days < 0 or not 1 <= args.page_size <= 10000 or (args.max_records is not None and args.max_records < 1):
        parser.error("invalid overlap/page-size/max-records")
    return args


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"day", "month"}:
        from sec_filings_legacy import main as legacy_main
        print("Using legacy SEC envelope; shared pipeline commands are daily/historical.", file=sys.stderr)
        return legacy_main(argv)
    args = arguments(argv)
    try:
        settings = StorageSettings.load(args.storage_config, {"backend": args.backend, "local_root": args.output_root,
            "s3_bucket": args.s3_bucket, "s3_prefix": args.s3_prefix, "region": args.region})
        universe, taxonomy = load_json(args.universe), load_json(args.taxonomy)
        matcher = CompanyMatcher(universe, args.company_id, args.sector)
        scope = {"selection": args.selection, "company_ids": sorted(matcher.companies), "sectors": sorted(set(args.sector)),
                 "ciks": sorted(set(args.cik)), "forms": sorted(set(args.form)), "date_basis": "filing_date_america_new_york"}
        if args.selection == "universe" and not matcher.companies:
            raise ValueError("selected universe contains no enabled companies")
        if args.index_file:
            if settings.backend != "local":
                raise ValueError("offline index fixtures may only write to local storage")
            raw = args.index_file.read_bytes()
            scope["offline_fixture_sha256"] = hashlib.sha256(raw).hexdigest()

            class FileClient:
                def fetch(self, year, quarter):
                    return raw
            client = FileClient()
        else:
            client = SECClient(args.user_agent)
        store = settings.store()
        today = datetime.now(NY).date()
        start = args.start or args.origin or today - timedelta(days=1)
        end = args.end if args.mode == "historical" else (args.start + timedelta(days=1) if args.start else today)
        probe = make_spec(start, start + timedelta(days=1), args.mode, scope, universe, taxonomy)
        previous = read_watermark(store, probe)
        if args.mode == "daily" and args.start is None and previous is None and args.origin is None:
            raise ValueError("first automatic daily run requires --origin YYYY-MM-DD")
        origin = parse_instant(previous["origin"]).astimezone(NY).date() if previous else (args.origin or start)
        if args.origin and args.origin != origin:
            raise ValueError("--origin disagrees with the stored stream origin")
        if args.mode == "daily" and args.start is None:
            boundary = parse_instant(previous["completed_until"]).astimezone(NY).date() if previous else origin
            start = max(origin, boundary - timedelta(days=args.overlap_days))
        if args.mode == "daily" and args.start is None and start == end:
            print(json.dumps({"status": "up_to_date", "completed_until": midnight(end)}))
            return 0
        if start >= end or end > today or start < date(1994, 7, 1):
            raise ValueError("use a nonempty range from 1994-07-01 through completed New York calendar days")
        if args.index_file and quarter_of(start) != quarter_of(end - timedelta(days=1)):
            raise ValueError("one offline fixture cannot span multiple quarters")
        cache, results = {}, []
        for window_start, window_end in windows(start, end, args.mode):
            refresh = args.refresh
            if args.mode == "daily" and args.start is None and previous:
                refresh = args.refresh or window_start < parse_instant(previous["completed_until"]).astimezone(NY).date()
            result = collect_window(store, settings, universe, taxonomy, client, window_start, window_end,
                                    args.mode, scope, matcher, cache, refresh, args.page_size, args.max_records)
            if result["status"] == "complete":
                try:
                    boundary = advance_watermark(store, result["manifest"], midnight(origin))
                    result["completed_until"] = boundary["completed_until"]
                except ValueError:
                    result["watermark_status"] = "coverage_gap_not_advanced"
            results.append(result)
            print(json.dumps(result), flush=True)
            if result["status"] != "complete":
                break
        return 0 if all(r["status"] == "complete" for r in results) else 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"SEC collection stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
