#!/usr/bin/env python3
"""Shared, resumable collection for clinical and regulatory sources."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from collection_storage import (AlreadyComplete, CollectionRun, Conflict, StorageSettings,
    advance_watermark, now, task_spec, write_checked, write_json)
from research_contract import ROOT, COLLECTION_UNIVERSE, canonical_json, digest, load_json, seal_record
from sec_filings import normalize_name

VERSION = "regulatory-1.0"
SOURCES = ("clinicaltrials", "fda", "ema", "chictr", "nmpa", "uk", "japan")


class SourceIssue(RuntimeError):
    def __init__(self, code, partial=False, diagnostics=None):
        super().__init__(code)
        self.code, self.partial = code, partial
        self.diagnostics = diagnostics


def require(value, code):
    if not value:
        raise SourceIssue(code)


class EvidenceClient:
    """Persist successful source responses; never persist tokens or API keys."""
    def __init__(self, store, source, opener=urlopen, sleeper=time.sleep):
        self.store, self.source, self.opener, self.sleep = store, source, opener, sleeper
        self.evidence = []
        self.last_request = 0

    def save(self, raw, url, media="application/json"):
        checksum = hashlib.sha256(raw).hexdigest()
        key = f"source_documents/{self.source}/{checksum}"
        write_checked(self.store, key, raw, content_type=media)
        self.evidence.append({"key": key, "sha256": checksum, "source_url": url, "retrieved_at": now()})
        return raw

    def get(self, url, params=None, body=None, api_key=None, no_matches=False):
        is_fda = urlsplit(url).hostname == 'api.fda.gov'
        opener = self.opener
        if is_fda:
            require(urlsplit(url).scheme == 'https', 'openfda_requires_https')
            if not api_key:
                from fda_access import api_key as resolve_fda_key
                api_key = resolve_fda_key()
        public_url = url + ("?" + urlencode(params) if params else "")
        request_params = dict(params or {})
        if api_key and not is_fda:
            request_params["api_key"] = api_key
        request_url = url + ("?" + urlencode(request_params) if request_params else "")
        headers = {"User-Agent": "Optima Holdings support@optima-holdings.com", "Accept-Encoding": "identity"}
        if is_fda:
            import base64
            headers['Authorization'] = 'Basic ' + base64.b64encode((api_key + ':').encode()).decode()
            if opener is urlopen:
                from urllib.request import build_opener
                from fda_access import NoRedirect
                opener = build_opener(NoRedirect()).open
        if body is not None:
            headers["Content-Type"] = "application/json"
        for attempt in range(4):
            self.sleep(max(0, 0.3 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                with opener(Request(request_url, data=canonical_json(body) if body is not None else None,
                                         headers=headers), timeout=60) as response:
                    raw = response.read(64 * 1024 * 1024 + 1)
                    require(len(raw) <= 64 * 1024 * 1024, "response_too_large")
                    length = response.headers.get("Content-Length")
                    require(length is None or int(length) == len(raw), "truncated_response")
                    media = response.headers.get("Content-Type", "application/octet-stream")
                return self.save(raw, public_url, media)
            except HTTPError as exc:
                if no_matches and exc.code == 404:
                    error = exc.read()
                    if b"No matches found" in error:
                        self.save(error, public_url)
                        return b'{"meta":{"results":{"total":0}},"results":[]}'
                if exc.code not in {429, 500, 502, 503, 504}:
                    raise SourceIssue(f"source_http_{exc.code}") from None
                retry = exc.headers.get("Retry-After", "0") if exc.headers else "0"
                try:
                    delay = max(2 ** attempt, float(retry))
                except ValueError:
                    raise SourceIssue("retry_deferred", True) from None
                if delay > 30:
                    raise SourceIssue("retry_deferred", True) from None
                if attempt < 3:
                    self.sleep(delay)
            except (URLError, TimeoutError):
                if attempt < 3:
                    self.sleep(2 ** attempt)
        raise SourceIssue("source_retries_exhausted", True)

    def json(self, *args, **kwargs):
        try:
            result = json.loads(self.get(*args, **kwargs))
        except (ValueError, UnicodeDecodeError):
            raise SourceIssue("invalid_json") from None
        require(isinstance(result, dict), "invalid_response_shape")
        return result

    def rendered(self, url, actions=None, delay=3, pending_validator=None):
        from decodo_scraping_api import ScrapeError, cached_token, scrape_content
        token = cached_token()
        host = urlsplit(url).hostname
        table_class = None
        if host == "www.chinadrugtrials.org.cn":
            table_class = "searchDetailTable" if "searchlistdetail.dhtml" in url else "searchTable"
        browser_actions = list(actions or []) + [{"type": "wait_for_element",
            "selector": {"type": "css", "value": "table." + table_class if table_class else "table"},
            "timeout_s": 15, "on_error": "error"}]
        for attempt in range(4):
            self.sleep(delay if attempt == 0 else max(delay, 2 ** attempt))
            try:
                parameters = {'proxy_pool': 'premium', 'headless': 'html',
                              'browser_actions': browser_actions}
                if host != 'www.chinadrugtrials.org.cn':
                    parameters['geo'] = 'China'
                text = scrape_content(url, token, pending_validator=pending_validator, **parameters)
            except ScrapeError as exc:
                # Gateway throttling affects the account, not this page. Do not
                # spend the bounded retry loop immediately repeating a 429.
                # Leave the cursor intact for a later scheduled invocation.
                if exc.stage == "gateway" and exc.status == 429:
                    raise SourceIssue(str(exc), True, {"source_url": url,
                        "stage": exc.stage, "http_status": exc.status,
                        "attempts": attempt + 1, "retry_policy": "next_scheduled_invocation"}) from None
                # These public registries intermittently return 405 during
                # browser initialization. One ordinary reload is bounded;
                # verification requirements still stop collection.
                if (exc.retryable and attempt < 3) or (exc.stage == "target" and exc.status == 405 and attempt == 0):
                    continue
                raise SourceIssue(str(exc), True, {"source_url": url, "stage": exc.stage,
                    "http_status": exc.status, "attempts": attempt + 1}) from None
            except Exception as exc:
                raise SourceIssue("rendered_source_unavailable", True,
                    {"source_url": url, "error_type": type(exc).__name__, "attempts": attempt + 1}) from None
            # Keep incomplete and verification responses as evidence too.
            self.save(text.encode(), url, "text/html")
            require(not any(s in text.lower() for s in ("滑动验证码", "验证码", "request has been blocked", "<title>405</title>")), "source_verification_required")
            tables = re.findall(r"<table\b[^>]*>", text, re.I)
            ready = any(table_class in table for table in tables) if table_class else bool(tables)
            if ready:
                return text
            if attempt == 3:
                raise SourceIssue("rendered_document_incomplete", True,
                    {"source_url": url, "stage": "document", "expected_selector": browser_actions[-1]["selector"]["value"], "attempts": 4})


class CompanyMatcher:
    """Exact normalized names nominate candidates; they never verify identity."""
    def __init__(self, universe, sectors=()):
        self.companies = {c["company_id"]: c for c in universe["companies"]
            if c["collection_enabled"] and c["review_status"] != "rejected" and
            (not sectors or any(s["sector_id"] in sectors and s["review_status"] != "rejected" for s in c["sectors"]))}
        self.names = {}
        names = [(c["canonical_name"], cid) for cid, c in self.companies.items()]
        names += [(a["alias"], a["company_id"]) for a in universe["company_aliases"]
                  if a["review_status"] != "rejected" and a["company_id"] in self.companies]
        for name, cid in names:
            normalized = normalize_name(name)
            if normalized:
                self.names.setdefault(normalized, set()).add(cid)

    def match(self, names):
        ids = set()
        for name in names:
            if isinstance(name, str):
                ids.update(self.names.get(normalize_name(name), ()))
        sectors = {s["sector_id"] for cid in ids for s in self.companies[cid]["sectors"] if s["review_status"] != "rejected"}
        return sorted(ids), sorted(sectors)


def stamp(value):
    return {"value": value, "precision": "day", "source_timezone": None} if value else None


def normalize(item, run, matcher, evidence, observed_at):
    candidates, sectors = matcher.match(item.get("company_names", []))
    payload = {"provider_id": item["id"], "record_type": item["kind"], "data": item["data"],
        "title": item.get("title"), "company_names": item.get("company_names", []),
        "candidate_company_ids": candidates, "candidate_sector_ids": sectors,
        "company_match_basis": "unverified_name", "date_basis": item["date_basis"],
        "coverage_note": item.get("coverage_note"), "source_evidence": evidence}
    return seal_record({"document_type": "collected_record", "schema_version": "1.0",
        "source": run.spec["source"], "dataset": run.spec["dataset"], "source_record_id": item["id"],
        "source_record_id_basis": item.get("identity_basis", "provider"), "source_url": item["url"],
        "universe_version": run.universe["universe_version"], "company_ids": [], "listing_ids": [],
        "product_ids": [], "person_ids": [], "entity_match_status": "unresolved",
        "event_at": stamp(item.get("date")), "available_at": None,
        "source_updated_at": stamp(item.get("updated")), "ingested_at": observed_at,
        "availability_basis": "unknown", "availability_evidence": [], "run_id": run.run_id,
        "payload": payload})


def instant(day):
    return day.isoformat() + "T00:00:00Z"


def collect(store, settings, universe, taxonomy, source, start, end, mode, adapter,
            selection="all", sectors=(), page_size=100, max_pages=None, refresh=False, client=None):
    matcher = CompanyMatcher(universe, sectors)
    scope = {"selection": selection, "sectors": sorted(set(sectors)), "page_size": page_size,
             "date_basis": adapter.date_basis, "coverage": adapter.coverage}
    if getattr(adapter, "registry_ids", ()):
        scope["registry_ids"] = list(adapter.registry_ids)
    spec = task_spec(adapter.source, "research_records", mode, instant(start), instant(end), scope, VERSION, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=not refresh, refresh=refresh)
    except AlreadyComplete as exc:
        return {"status": "complete", "already_complete": True, "manifest": str(exc)}
    client = client or EvidenceClient(store, adapter.source)
    pages = 0
    try:
        state = json.loads(run.cursor) if run.cursor else {}
        seen = set()
        for page in run.state["pages"]:
            input_key = (f"manifests/collection_runs/source={adapter.source}/dataset=research_records/"
                         f"{page['run_id']}/inputs/{page['sequence']:08d}.json")
            receipt = store.get(input_key)
            require(receipt is not None, "missing_committed_input_receipt")
            input_page = json.loads(receipt.body)
            if "provider_ids" in input_page:
                seen.update(input_page["provider_ids"])
            else:
                require(input_page["source_records"] == input_page["selected_records"], "resume_requires_source_identity_receipt")
            for batch in page["batches"]:
                for line in store.get(batch["key"]).body.splitlines():
                    seen.add(json.loads(line)["source_record_id"])
        while not run.exhausted:
            if max_pages is not None and pages >= max_pages:
                return {"status": "partial", "reason": "page_limit", "manifest": run.finish("partial", "page_limit")}
            client.evidence = []
            items, following, exhausted = adapter.page(client, start, end, mode, state, page_size)
            require(exhausted or following != state, "pagination_did_not_advance")
            records = []
            observed_at = now()
            for item in items:
                require(item["id"] not in seen, "duplicate_provider_record")
                seen.add(item["id"])
                record = normalize(item, run, matcher, client.evidence, observed_at)
                if selection == "all" or record["payload"]["candidate_company_ids"]:
                    records.append(record)
            sequence = len(run.state["pages"])
            write_json(store, f"{run.state['manifest_prefix']}/inputs/{sequence:08d}.json", {
                "evidence": client.evidence, "cursor_before": state, "cursor_after": following,
                "provider_ids": [item["id"] for item in items],
                "source_records": len(items), "selected_records": len(records), "exhausted": exhausted})
            run.commit_page(records, next_cursor=json.dumps(following, sort_keys=True) if not exhausted else None, exhausted=exhausted)
            state, pages = following, pages + 1
        manifest = run.finish("complete", expected_records=run.state["record_count"])
        return {"status": "complete", "manifest": manifest, "records": run.state["record_count"]}
    except SourceIssue as exc:
        status = "partial" if exc.partial else "failed"
        diagnostics_key = f"{run.state['manifest_prefix']}/failure.json"
        write_json(store, diagnostics_key, {"reason": exc.code, "diagnostics": exc.diagnostics,
            "evidence": client.evidence, "cursor": run.cursor})
        manifest = run.finish(status, exc.code)
        # A saved page total/revision can become stale between scheduled runs.
        # Preserve that attempt, then start one fresh snapshot within the
        # remaining page budget instead of retrying its invalid cursor forever.
        remaining = None if max_pages is None else max_pages - pages
        if (exc.code == "source_changed_during_pagination" and not refresh
                and run.state.get("pages") and (remaining is None or remaining > 0)):
            result = collect(store, settings, universe, taxonomy, source, start, end, mode,
                             adapter, selection, sectors, page_size, remaining, True, client)
            return {**result, "refreshed_from_manifest": manifest}
        return {"status": status, "reason": exc.code, "manifest": manifest,
                "diagnostics": diagnostics_key}
    except KeyboardInterrupt:
        return {"status": "partial", "reason": "interrupted", "manifest": run.finish("partial", "interrupted")}
    except Conflict:
        raise
    except Exception as exc:
        if run.pending_final is None:
            manifest = run.finish("failed", "collection_error")
            return {"status": "failed", "reason": "collection_error", "error_type": type(exc).__name__, "manifest": manifest}
        raise


def main(source, argv=None):
    from historical_policy import add_end_option, resolve_dates
    from regulatory_sources import ADAPTERS
    parser = argparse.ArgumentParser(description="Shared clinical/regulatory collection; END is exclusive.")
    add_end_option(parser)
    parser.add_argument("mode", choices=("historical", "daily"))
    parser.add_argument("start", nargs="?", type=date.fromisoformat)
    parser.add_argument("end", nargs="?", type=date.fromisoformat)
    parser.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    parser.add_argument("--backend", choices=("local", "s3"))
    parser.add_argument("--output-root")
    parser.add_argument("--universe", type=Path, default=COLLECTION_UNIVERSE)
    parser.add_argument("--taxonomy", type=Path, default=ROOT / "config/sectors.v1.json")
    parser.add_argument("--selection", choices=("all", "universe"), default="all")
    parser.add_argument("--sector", action="append", choices=("biotech", "robotics", "semiconductors", "energy_storage"), default=[])
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--lookback-days", type=int, default=0, help="daily reconciliation extends the source date window backward")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--registry-id", action="append", default=[],
                        help="NMPA only: explicit verification cohort; never implies whole-registry coverage")
    args = parser.parse_args(argv)
    resolve_dates(parser, args, args.mode)
    if args.registry_id and source != "nmpa":
        parser.error("--registry-id is supported only for NMPA")
    if args.registry_id:
        import re
        if not all(re.fullmatch(r"CTR20\d{6,}", value) for value in args.registry_id):
            parser.error("invalid NMPA registration number")
    if args.sector and args.selection != "universe":
        parser.error("--sector requires --selection universe; default all retains unmatched discovery records")
    if not 1 <= args.page_size <= 1000 or (args.max_pages is not None and args.max_pages < 1) or args.lookback_days < 0:
        parser.error("invalid page-size, max-pages or lookback-days")
    today = datetime.now(timezone.utc).date()
    if args.mode == "historical":
        if args.start is None or args.end is None:
            parser.error("historical requires START END")
        start, end = args.start, args.end
    else:
        if args.end:
            parser.error("daily accepts one date")
        end = (args.start or today - timedelta(days=1)) + timedelta(days=1)
        start = end - timedelta(days=1 + args.lookback_days)
    if start >= end or end > today:
        parser.error("use a nonempty range of completed UTC days")
    settings = StorageSettings.load(args.storage_config, {"backend": args.backend, "local_root": args.output_root})
    store = settings.store()
    universe, taxonomy = load_json(args.universe), load_json(args.taxonomy)
    cursor = start
    try:
        while cursor < end:
            next_month = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
            following = min(next_month, end) if args.mode == "historical" else end
            adapter = ADAPTERS[source](registry_ids=args.registry_id) if source == "nmpa" else ADAPTERS[source]()
            result = collect(store, settings, universe, taxonomy, source, cursor, following, args.mode,
                adapter, args.selection, args.sector, args.page_size, args.max_pages,
                args.refresh)
            if result["status"] == "complete":
                # Explicit invocations may be disjoint; never silently advance over gaps.
                try:
                    manifest = json.loads(store.get(result["manifest"]).body)
                    from collection_storage import read_watermark
                    previous = read_watermark(store, manifest["task"])
                    origin = previous["origin"] if previous else instant(start)
                    result["completed_until"] = advance_watermark(store, result["manifest"], origin)["completed_until"]
                except ValueError:
                    result["watermark_status"] = "coverage_gap_not_advanced"
            print(json.dumps({"collector": source, "start": str(cursor), "end": str(following), **result}), flush=True)
            if result["status"] != "complete":
                return 2
            cursor = following
        return 0
    except Exception as exc:
        # Provider URLs can include credentials; log only a non-secret error type.
        print(f"Collection stopped: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2:]))
