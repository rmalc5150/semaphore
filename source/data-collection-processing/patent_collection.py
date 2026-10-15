#!/usr/bin/env python3
"""Resumable USPTO discovery and evidence-preserving global patent JSONL imports."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_checked, write_json
from patent_landscape import normalize_org
from regulatory_collection import CompanyMatcher, EvidenceClient, SourceIssue, instant, require
from research_contract import COLLECTION_UNIVERSE, ROOT, canonical_json, digest, load_json, seal_record

VERSION = "patents-1.0"
RULES_PATH = ROOT / "config/patent-classification.v1.json"
SEARCH_URL = "https://api.uspto.gov/api/v1/patent/applications/search"
TABLE_URL = "https://console.cloud.google.com/bigquery?p=patents-public-data&d=patents&t=publications&page=table"
MAX_EXPORT_BYTES = 256 * 1024 * 1024


def day(value):
    if value in (None, "", 0, "0"):
        return None
    value = str(value)
    if re.fullmatch(r"\d{8}", value):
        value = f"{value[:4]}-{value[4:6]}-{value[6:]}"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("patent date must be YYYY-MM-DD or YYYYMMDD")
    return date.fromisoformat(value).isoformat()


def strings(value):
    require(isinstance(value, list) and all(isinstance(x, str) for x in value), "invalid_string_array")
    return sorted(set(value))


def classify(record, rules):
    # Word boundaries prevent e.g. 'rna' matching 'internal'. Scores would imply
    # calibration we do not have, so retain the actual rule evidence instead.
    text = normalize_org(" ".join([record.get("title") or "", record.get("abstract") or ""]))
    codes = [re.sub(r"\s|/", "", c.upper()) for c in record.get("cpc_codes", [])]
    result = []
    for rule in rules["rules"]:
        cpc = sorted(p for p in rule["cpc_prefixes"] if any(c.startswith(p) for c in codes))
        terms = sorted(t for t in rule["terms"] if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", text))
        if cpc or terms:
            result.append({"sector_id": rule["sector_id"], "category": rule["category"],
                           "cpc_hits": cpc, "term_hits": terms, "review_status": "pending"})
    return result


class PatentMatcher(CompanyMatcher):
    def __init__(self, universe):
        super().__init__(universe)
        self.names = {}
        names = [(c["canonical_name"], cid) for cid, c in self.companies.items()]
        names += [(a["alias"], a["company_id"]) for a in universe["company_aliases"]
                  if a["review_status"] != "rejected" and a["company_id"] in self.companies]
        for name, cid in names:
            normalized = normalize_org(name)
            if normalized:
                self.names.setdefault(normalized, set()).add(cid)

    def match(self, names):
        ids = set().union(*(self.names.get(normalize_org(n), set()) for n in names)) if names else set()
        sectors = {s["sector_id"] for cid in ids for s in self.companies[cid]["sectors"] if s["review_status"] != "rejected"}
        return sorted(ids), sorted(sectors)


def export_record(row):
    require(isinstance(row, dict), "invalid_export_row")
    pub = row.get("publication_number")
    require(isinstance(pub, str) and bool(re.fullmatch(r"[A-Z]{2}-?[A-Za-z0-9-]+", pub)), "missing_publication_identity")
    result = {k: row.get(k) for k in ("application_number", "family_id", "title", "abstract")}
    result.update(publication_number=pub, country_code=row.get("country_code") or pub[:2],
        kind_code=row.get("kind_code"), cpc_codes=strings(row.get("cpc_codes") or []),
        assignees=strings(row.get("assignees") or []), applicants=[])
    for field in ("filing_date", "priority_date", "publication_date", "grant_date"):
        result[field] = day(row.get(field))
    # A prior export's matched_company is not evidence of legal ownership.
    return result


def odp_record(row):
    require(isinstance(row, dict), "invalid_odp_row")
    number = row.get("applicationNumberText")
    require(isinstance(number, str) and bool(re.fullmatch(r"(?:\d{8}|PCT[A-Z]{2}\d{10})", number)), "invalid_application_identity")
    meta = row.get("applicationMetaData")
    require(isinstance(meta, dict), "missing_application_metadata")
    applicants = [a["applicantNameText"] for a in meta.get("applicantBag", []) if a.get("applicantNameText")]
    if meta.get("firstApplicantName"):
        applicants.append(meta["firstApplicantName"])
    return {"application_number": number, "publication_number": meta.get("earliestPublicationNumber"),
        "patent_number": meta.get("patentNumber"),
        "country_code": (meta.get("earliestPublicationNumber") or ("WO" if number.startswith("PCT") else "US"))[:2],
        "family_id": None,
        "title": meta.get("inventionTitle"), "abstract": None,
        "filing_date": day(meta.get("filingDate")), "publication_date": day(meta.get("earliestPublicationDate")),
        "grant_date": day(meta.get("grantDate")), "status_date": day(meta.get("applicationStatusDate")),
        "status": meta.get("applicationStatusDescriptionText"),
        "cpc_codes": strings(meta.get("cpcClassificationBag") or []),
        "applicants": strings(applicants), "assignees": [],
        "provider_last_ingestion": row.get("lastIngestionDateTime"),
        "source_events": row.get("eventDataBag", [])}


def envelope(data, identity, run, matcher, rules, evidence, observed, source_url):
    candidates, sectors = matcher.match(data["assignees"] + data["applicants"])
    return seal_record({"document_type": "collected_record", "schema_version": "1.0",
        "source": run.spec["source"], "dataset": "patent_records", "source_record_id": identity,
        "source_record_id_basis": "provider", "source_url": source_url,
        "universe_version": run.universe["universe_version"], "company_ids": [], "listing_ids": [],
        "product_ids": [], "person_ids": [], "entity_match_status": "unresolved", "event_at": None,
        "available_at": None, "source_updated_at": None, "ingested_at": observed,
        "availability_basis": "unknown", "availability_evidence": [], "run_id": run.run_id,
        "payload": {"record_type": "patent_snapshot", "data": data,
            "candidate_company_ids": candidates, "candidate_sector_ids": sectors,
            "company_match_basis": "unverified_exact_normalized_name",
            "technology_classifications": classify(data, rules), "classification_version": rules["version"],
            "review_required": True, "date_basis": run.spec["scope"]["date_basis"],
            "source_evidence": evidence,
            "coverage_note": "Current source snapshot; historical event dates do not prove point-in-time field availability."}})


def collection_task(universe, taxonomy, source, start, end, mode, scope, rules):
    scope = {**scope, "classification_hash": digest(rules), "selection": "all_returned_records"}
    return task_spec(source, "patent_records", mode, instant(start), instant(end), scope, VERSION, universe, taxonomy)


def start_run(store, settings, universe, taxonomy, source, start, end, mode, scope, rules, refresh):
    write_json(store, f"manifests/configurations/patent_classification/{digest(rules)}.json", rules)
    spec = collection_task(universe, taxonomy, source, start, end, mode, scope, rules)
    return CollectionRun.start(store, spec, universe, taxonomy, settings, resume=not refresh, refresh=refresh)


def outcome(run, status, reason=None):
    return {"status": status, "reason": reason, "records": run.state["record_count"],
            "manifest": run.finish(status, reason, expected_records=run.state["record_count"] if status == "complete" else None)}


def import_export(store, settings, universe, taxonomy, path, start, end, mode="historical",
                  date_basis="filing_date", page_size=100, max_pages=100, refresh=False, rules=None):
    require(date_basis in {"filing_date", "publication_date"}, "invalid_date_basis")
    require(1 <= page_size <= 1000 and max_pages > 0, "invalid_limits")
    rules = rules or load_json(RULES_PATH)
    with Path(path).open("rb") as handle:
        raw = handle.read(MAX_EXPORT_BYTES + 1)
    require(len(raw) <= MAX_EXPORT_BYTES, "export_too_large_split_into_files")
    # Validate the entire file before opening a run. Conflicting duplicate rows
    # are retained as separate source revisions; byte-equivalent normalized rows
    # are deduplicated. Nothing gets silently overwritten by publication number.
    rows, seen = [], set()
    for line in raw.splitlines():
        if not line.strip():
            continue
        data = export_record(json.loads(line))
        basis = data[date_basis]
        require(basis is not None and start.isoformat() <= basis < end.isoformat(), "export_outside_window_or_missing_date")
        checksum = digest(data)
        if checksum not in seen:
            rows.append(data)
            seen.add(checksum)
    checksum = hashlib.sha256(raw).hexdigest()
    key = f"source_documents/google_patents_bigquery/{checksum}"
    scope = {"input_sha256": checksum, "date_basis": date_basis, "page_size": page_size,
        "coverage": "Provided export only; original query scope, job metadata and dataset freshness are unverified."}
    try:
        run = start_run(store, settings, universe, taxonomy, "google_patents_bigquery", start, end, mode, scope, rules, refresh)
    except AlreadyComplete as exc:
        return {"status": "complete", "already_complete": True, "manifest": str(exc)}
    try:
        write_checked(store, key, raw, content_type="application/x-ndjson")
        evidence = [{"key": key, "sha256": checksum, "source_url": TABLE_URL,
                     "retrieved_at": None, "imported_at": run.started_at, "original_export_time": None}]
        matcher = PatentMatcher(universe)
        offset = int(run.cursor or 0)
        pages = 0
        while not run.exhausted:
            if pages >= max_pages:
                return outcome(run, "partial", "page_limit")
            batch = rows[offset:offset + page_size]
            records = [envelope(r, r["publication_number"], run, matcher, rules, evidence, run.started_at,
                                "https://patents.google.com/patent/" + r["publication_number"]) for r in batch]
            offset += len(batch)
            exhausted = offset == len(rows)
            run.commit_page(records, next_cursor=None if exhausted else str(offset), exhausted=exhausted)
            pages += 1
        return outcome(run, "complete")
    except Exception:
        if not run.closed:
            run.finish("failed", "import_failed")
        raise


class ODPClient(EvidenceClient):
    def __init__(self, store, key_loader=None, opener=urlopen, sleeper=time.sleep, gate=None):
        super().__init__(store, "uspto_odp", opener, sleeper)
        if key_loader is None:
            from uspto_patents import load_api_key
            key_loader = load_api_key
        self.key_loader, self.key = key_loader, None
        from uspto_rate_limit import pace
        self.gate = gate or pace

    def search(self, query):
        return self._request(SEARCH_URL, query)

    def application(self, number):
        from uspto_patents import application_number, BASE_URL
        return self._request(BASE_URL + "/" + application_number(number))

    def _request(self, url, query=None):
        if self.key is None:
            self.key = self.key_loader()
        headers = {"X-API-KEY": self.key, "Content-Type": "application/json", "Accept": "application/json"}
        for attempt in range(4):
            self.gate()
            self.sleep(max(0, 1 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                with self.opener(Request(url, data=canonical_json(query) if query is not None else None, headers=headers), timeout=60) as response:
                    raw = response.read(64 * 1024 * 1024 + 1)
                    require(len(raw) <= 64 * 1024 * 1024, "response_too_large")
                    length = response.headers.get("Content-Length")
                    require(length is None or int(length) == len(raw), "truncated_response")
                result = json.loads(raw)
                self.save(raw, url)
                return result
            except HTTPError as exc:
                if exc.code == 404:
                    raw = exc.read(65536)
                    try:
                        empty = json.loads(raw)
                    except ValueError:
                        empty = {}
                    if empty.get("detailedMessage") == "No matching records found, refine your search criteria and try again":
                        self.save(raw, url)
                        return {"count": 0, "patentFileWrapperDataBag": []}
                if exc.code not in {429, 500, 502, 503, 504}:
                    raise SourceIssue(f"source_http_{exc.code}") from None
                try:
                    delay = max(2 ** attempt, float(exc.headers.get("Retry-After", "0")))
                except (ValueError, AttributeError):
                    raise SourceIssue("retry_deferred", True) from None
                if delay > 30:
                    raise SourceIssue("retry_deferred", True) from None
                if attempt < 3:
                    self.sleep(delay)
            except (URLError, TimeoutError):
                if attempt < 3:
                    self.sleep(2 ** attempt)
        raise SourceIssue("source_retries_exhausted", True)


def search_query(start, end, mode, offset, page_size):
    field = "applicationMetaData.filingDate" if mode == "historical" else "lastIngestionDateTime"
    # Provider timestamps omit timezone. The query uses provider calendar days;
    # the UTC envelope boundaries are labels, not a claim about their timezone.
    lo = start.isoformat() + ("T00:00:00" if mode == "daily" else "")
    hi = end.isoformat() + ("T00:00:00" if mode == "daily" else "")
    return {"q": f"{field}:[{lo} TO {hi}}}", "pagination": {"offset": offset, "limit": page_size},
            "sort": [{"field": "applicationNumberText", "order": "asc"}]}


def collect_uspto(store, settings, universe, taxonomy, start, end, mode, page_size=50,
                  max_pages=10, refresh=False, client=None, rules=None, query_bounds=None,
                  partition_parent=None):
    require(1 <= page_size <= 100 and max_pages > 0, "invalid_limits")
    rules = rules or load_json(RULES_PATH)
    scope = {"date_basis": "filing_date" if mode == "historical" else "provider_last_ingestion_day",
        "provider_timezone": "unknown", "page_size": page_size,
        "query": search_query(start, end, mode, 0, page_size)["q"],
        "coverage": "USPTO public API results only; mutable index, no snapshot isolation or global coverage."}
    if query_bounds:
        require(mode == 'daily' and len(query_bounds) == 2, 'invalid_query_partition')
        lower, upper = map(datetime.fromisoformat, query_bounds)
        require(datetime.combine(start, datetime.min.time()) <= lower < upper <=
                datetime.combine(end, datetime.min.time()), 'invalid_query_partition')
        scope.update(query=f'lastIngestionDateTime:[{query_bounds[0]} TO {query_bounds[1]}}}',
                     query_bounds=list(query_bounds), partition_parent=partition_parent)
    try:
        run = start_run(store, settings, universe, taxonomy, "uspto_odp", start, end, mode, scope, rules, refresh)
    except AlreadyComplete as exc:
        return {"status": "complete", "already_complete": True, "manifest": str(exc), "pages_requested": 0}
    client = client or ODPClient(store)
    matcher, pages = PatentMatcher(universe), 0
    state = json.loads(run.cursor) if run.cursor else {"offset": 0, "total": None, "last_id": None}
    effective_size = state.get('effective_page_size', page_size)
    try:
        while not run.exhausted:
            if pages >= max_pages:
                return {**outcome(run, "partial", "page_limit"), 'pages_requested': pages}
            client.evidence = []
            query = search_query(start, end, mode, state["offset"], effective_size)
            query['q'] = scope['query']
            pages += 1
            try:
                result = client.search(query)
            except SourceIssue as exc:
                if exc.code != 'source_http_413' or effective_size == 1:
                    raise
                # Retry the same offset; a rejected page commits no records.
                # Keep the task identity stable and persist the smaller size
                # with the next successful checkpoint. Failed requests consume
                # the invocation budget too.
                effective_size = max(1, effective_size // 2)
                continue
            require(isinstance(result, dict), "invalid_response_shape")
            total, rows = result.get("count"), result.get("patentFileWrapperDataBag")
            require(type(total) is int and total >= 0 and isinstance(rows, list), "invalid_search_response")
            if state["total"] is not None and total != state["total"]:
                raise SourceIssue("source_changed_refresh_required", True)
            require(len(rows) == min(effective_size, total - state["offset"]), "incomplete_page")
            records, previous = [], state["last_id"]
            observed = now()
            for row in rows:
                data = odp_record(row)
                identity = data["application_number"]
                require(previous is None or identity > previous, "nonmonotonic_pagination")
                basis = data["filing_date"] if mode == "historical" else (data["provider_last_ingestion"] or "")[:10]
                require(basis is not None and start.isoformat() <= basis < end.isoformat(), "source_ignored_date_filter")
                if query_bounds:
                    timestamp = datetime.fromisoformat(data['provider_last_ingestion'])
                    require(lower <= timestamp < upper, 'source_ignored_partition_filter')
                records.append(envelope(data, identity, run, matcher, rules,
                    [dict(e, request=query) for e in client.evidence], observed,
                    f"https://data.uspto.gov/patent-file-wrapper/search/details/{identity}/application-data"))
                previous = identity
            state = {"offset": state["offset"] + len(rows), "total": total, "last_id": previous,
                     "effective_page_size": effective_size}
            exhausted = state["offset"] == total
            run.commit_page(records, next_cursor=None if exhausted else json.dumps(state, sort_keys=True), exhausted=exhausted)
        return {**outcome(run, "complete"), 'pages_requested': pages}
    except SourceIssue as exc:
        return {**outcome(run, "partial" if exc.partial else "failed", exc.code), 'pages_requested': pages}
    except Exception:
        if not run.closed:
            run.finish("failed", "collection_failed")
        raise


def collect_uspto_partitioned(store, settings, universe, taxonomy, start, end,
                              page_size=50, max_pages=10, refresh=False, client=None, rules=None):
    """Commit independent hourly scans before advancing the completed-day cursor.

    A changing hour restarts alone. Completed hours remain immutable observations,
    not a claim of a single source snapshot. Parent refresh gives children new IDs.
    """
    require(end == start + timedelta(days=1) and max_pages > 0, 'invalid_daily_partition_window')
    rules = rules or load_json(RULES_PATH)
    scope = {'date_basis': 'provider_last_ingestion_day', 'provider_timezone': 'unknown',
             'page_size': page_size, 'query': search_query(start, end, 'daily', 0, page_size)['q'],
             'partition_strategy': 'hourly-v1',
             'coverage': '24 independently observed hourly queries; mutable source, no snapshot isolation.'}
    try:
        run = start_run(store, settings, universe, taxonomy, 'uspto_odp', start, end, 'daily', scope, rules, refresh)
    except AlreadyComplete as exc:
        return {'status': 'complete', 'already_complete': True, 'manifest': str(exc)}
    client = client or ODPClient(store)
    hour, remaining = int(run.cursor or 0), max_pages
    try:
        # CollectionRun assigns a new attempt ID on resume. Follow its durable
        # ancestry so children retain their identity until an explicit refresh.
        ancestor = run.state
        while ancestor.get('resumed_from_run_id'):
            prefix = ancestor['manifest_prefix'].rsplit('/', 1)[0]
            ancestor = json.loads(store.get(prefix + '/' + ancestor['resumed_from_run_id'] + '/started.json').body)
        generation = ancestor['run_id']

        def scan(bounds, label):
            nonlocal remaining
            key = f'checkpoints/{run.task_id}/partitions/{generation}/{label}.json'
            saved = store.get(key)
            prior = json.loads(saved.body) if saved else {}
            lower, upper = map(datetime.fromisoformat, bounds)
            split = prior.get('split') or (prior.get('reason') == 'source_changed_refresh_required' and
                                           upper - lower > timedelta(minutes=5))
            if split:
                # Persist the plan before collecting children so interruption
                # cannot revert to the invalid larger offset scan.
                if not prior.get('split'):
                    write_json(store, key, {'split': True, 'prior_manifest': prior.get('manifest'),
                                           'query_bounds': bounds}, saved.token if saved else None)
                middle = lower + (upper - lower) / 2
                manifests = []
                for suffix, subrange in [('a', [bounds[0], middle.isoformat()]),
                                         ('b', [middle.isoformat(), bounds[1]])]:
                    child = scan(subrange, label + '-' + suffix)
                    if child['status'] != 'complete':
                        return child
                    manifests.extend(child['manifests'])
                return {'status': 'complete', 'manifests': manifests}
            if remaining <= 0:
                raise SourceIssue('page_limit', True)
            child = collect_uspto(store, settings, universe, taxonomy, start, end, 'daily',
                page_size, remaining, refresh=prior.get('reason') == 'source_changed_refresh_required',
                client=client, rules=rules, query_bounds=bounds, partition_parent=generation)
            write_json(store, key, child, saved.token if saved else None)
            remaining -= child['pages_requested']
            return {**child, 'manifests': [child['manifest']]}

        while not run.exhausted and hour < 24:
            if remaining <= 0:
                return outcome(run, 'partial', 'page_limit')
            lower = datetime.combine(start, datetime.min.time()) + timedelta(hours=hour)
            bounds = [lower.isoformat(), (lower + timedelta(hours=1)).isoformat()]
            child = scan(bounds, f'{hour:02}')
            if child['status'] != 'complete':
                return {**outcome(run, child['status'], child.get('reason')),
                        'partition_hour': hour, 'partition_manifest': child['manifest']}
            def records():
                for manifest_key in child['manifests']:
                    manifest = json.loads(store.get(manifest_key).body)
                    require(manifest['status'] == 'complete' and manifest['exhausted'], 'partition_not_complete')
                    for page in manifest['pages']:
                        for batch in page['batches']:
                            raw = store.get(batch['key']).body
                            require(hashlib.sha256(raw).hexdigest() == batch['sha256'], 'partition_batch_hash_mismatch')
                            lines = raw.splitlines()
                            require(len(lines) == batch['records'], 'partition_batch_count_mismatch')
                            for line in lines:
                                record = json.loads(line)
                                record['run_id'] = run.run_id
                                record['payload']['partition_manifest'] = manifest_key
                                yield seal_record(record)
            hour += 1
            run.commit_page(records(), next_cursor=str(hour) if hour < 24 else None, exhausted=hour == 24)
        return outcome(run, 'complete')
    except SourceIssue as exc:
        return outcome(run, 'partial' if exc.partial else 'failed', exc.code)
    except (Exception, KeyboardInterrupt):
        if not run.closed:
            run.finish('partial', 'partition_collection_interrupted')
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=["import", "uspto", "office-actions", "petition-decisions"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--mode", choices=["historical", "daily"], required=True)
    parser.add_argument("--start", type=date.fromisoformat, help="defaults to the shared start in historical mode; required for daily")
    parser.add_argument("--end", type=date.fromisoformat, required=True, help="exclusive boundary")
    parser.add_argument("--date-basis", choices=["filing_date", "publication_date"], default="filing_date")
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    parser.add_argument("--backend", choices=["local", "s3"])
    parser.add_argument("--output-root")
    parser.add_argument("--universe", type=Path, default=COLLECTION_UNIVERSE)
    parser.add_argument("--taxonomy", type=Path, default=ROOT / "config/sectors.v1.json")
    args = parser.parse_args(argv)
    if args.start is None:
        if args.mode == "daily":
            parser.error("daily requires --start")
        from historical_policy import historical_start
        args.start = historical_start()
    if args.end <= args.start or not 1 <= args.page_size <= 100 or args.max_pages < 1:
        parser.error("require start < end, page-size 1..100 and max-pages > 0")
    if args.source == "import" and not args.input:
        parser.error("import requires --input")
    settings = StorageSettings.load(args.storage_config, {"backend": args.backend, "local_root": args.output_root})
    common = [settings.store(), settings, load_json(args.universe), load_json(args.taxonomy)]
    kw = {"page_size": args.page_size, "max_pages": args.max_pages, "refresh": args.refresh}
    try:
        if args.source == "import":
            result = import_export(*common, args.input, args.start, args.end, args.mode, date_basis=args.date_basis, **kw)
        elif args.source == "uspto":
            result = collect_uspto(*common, args.start, args.end, args.mode, **kw)
        else:
            from patent_prosecution import collect, DATASETS
            result = collect(*common, DATASETS[0 if args.source == "office-actions" else 1],
                args.start, args.end, args.mode, **{**kw, "page_size": min(args.page_size, 20)})
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1
    print(json.dumps(result))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())
