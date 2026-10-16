#!/usr/bin/env python3
"""Bounded historical/daily news collection with shared evidence and checkpoints."""
import argparse
from datetime import date, datetime, timedelta, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from collection_operations import following_window, load_stored
from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json
from disclosure_collection import finish_error
from historical_policy import historical_start
from regulatory_collection import CompanyMatcher, EvidenceClient, SourceIssue, require, instant
from research_contract import ROOT, canonical_json, digest, load_json, parse_instant, seal_record

VERSION = "news-collection-1.0"
URLS = {"finlight": "https://api.finlight.me/v2/articles", "marketaux": "https://api.marketaux.com/v1/news/all"}


def query_text(provider, terms):
    def quoted(term):
        require(isinstance(term, str) and term.strip(), "empty_search_term")
        return '"' + term.replace('\\', '\\\\').replace('"', '\\"') + '"'
    require(terms, "empty_query")
    return (" OR " if provider == "finlight" else " | ").join(quoted(t) for t in terms)


def parameters(provider, query, language, start, end, page, size):
    # Include a one-second boundary overlap, then enforce [start,end) locally.
    # This handles providers' inclusive/exclusive time-filter differences.
    left = datetime.combine(start, datetime.min.time(), timezone.utc) - timedelta(seconds=1)
    if provider == "finlight":
        require(isinstance(language, str) and len(language) == 2, "finlight_requires_one_language")
        return {"query": query, "language": language, "from": left.isoformat(), "to": instant(end),
                "orderBy": "publishDate", "order": "ASC", "page": page, "pageSize": size}
    return {"search": query, "published_after": left.strftime("%Y-%m-%dT%H:%M:%S"),
            "published_before": end.isoformat() + "T00:00:00", "sort": "published_at",
            "group_similar": "false", "filter_entities": "false", "limit": size, "page": page,
            **({"language": language} if language else {})}


class NewsClient(EvidenceClient):
    def __init__(self, store, source, key, cap, max_requests=12, opener=urlopen, sleeper=time.sleep, capture_full_text=True):
        super().__init__(store, source, opener, sleeper)
        require(type(cap) is int and cap > 0 and type(max_requests) is int and max_requests > 0, "invalid_request_budget")
        self.key, self.cap, self.remaining = key, cap, max_requests
        self.capture_full_text = source in ('finlight', 'marketaux') and capture_full_text
        self.fulltext_api_reserve = 2

    def reserve(self):
        if self.remaining <= 0:
            raise SourceIssue("run_request_budget_reached", True)
        key = f"operations/news/budgets/{self.source}/{now()[:10]}.json"
        budget, token = load_stored(self.store, key)
        count = (budget or {}).get("requests_reserved", 0)
        if count >= self.cap:
            raise SourceIssue("daily_request_budget_reached", True)
        write_json(self.store, key, {"requests_reserved": count + 1, "updated_at": now()}, token)
        self.remaining -= 1

    def page(self, params):
        public = URLS[self.source]
        headers = {"User-Agent": "Optima Holdings support@optima-holdings.com", "Accept-Encoding": "identity"}
        if self.source == "finlight":
            headers.update({"X-API-KEY": self.key, "Content-Type": "application/json"})
            request = Request(public, data=canonical_json(params), headers=headers)
        else:
            public += "?" + urlencode(params)
            request = Request(public + "&" + urlencode({"api_token": self.key}), headers=headers)
        for attempt in range(3):
            self.reserve()  # Retries and ambiguous requests also consume the cap.
            self.sleep(1 if not attempt else 2 ** attempt)
            try:
                with self.opener(request, timeout=45) as response:
                    raw = response.read(16 * 1024 * 1024 + 1)
                require(len(raw) <= 16 * 1024 * 1024, "news_response_too_large")
                # Provider errors may echo a credential; never persist or print it.
                require(self.key.encode() not in raw, "news_response_contains_credential")
                data = json.loads(raw)
                require(isinstance(data, dict), "news_invalid_response")
                require(not data.get("error") and data.get("status") != "error", "news_provider_error")
                self.evidence = []
                self.save(raw, public)
                # POST parameters are evidence too, without authentication headers.
                self.save(canonical_json({"endpoint": URLS[self.source], "parameters": params}), URLS[self.source])
                return data
            except HTTPError as exc:
                # Discard the error body and private request URL, including chained exceptions.
                status = exc.code
                exc.close()
                if status == 429:
                    raise SourceIssue("news_provider_quota_or_rate_limit", True) from None
                if status in {401, 403}:
                    raise SourceIssue("news_authentication_or_entitlement_denied", True) from None
                if status not in {500, 502, 503, 504}:
                    raise SourceIssue("news_http_" + str(status)) from None
            except (URLError, TimeoutError):
                pass
            except (ValueError, UnicodeDecodeError):
                raise SourceIssue("news_invalid_json") from None
        raise SourceIssue("news_retries_exhausted", True)


def page_info(provider, data, page, requested_size):
    if provider == "finlight":
        require(data.get("status") == "ok" and data.get("page") == page, "finlight_page_invalid")
        rows, reported = data.get("articles"), data.get("pageSize")
        # Live responses use pageSize=0 for an empty result (rather than echoing
        # the request). Do not treat this field as the pagination stride or infer
        # completion from a short page; require an explicit empty page instead.
        require(isinstance(rows, list) and type(reported) is int and
                0 <= len(rows) <= requested_size and 0 <= reported <= requested_size,
                "finlight_page_shape_invalid")
        limit, total = requested_size, None
    else:
        meta = data.get("meta", {})
        require(meta.get("page") == page, "marketaux_page_invalid")
        rows, limit, total = data.get("data"), meta.get("limit"), meta.get("found")
        require(type(total) is int and total >= 0, "marketaux_total_invalid")
        require(isinstance(rows, list) and meta.get("returned") == len(rows), "marketaux_returned_mismatch")
    require(type(limit) is int and 0 < limit <= requested_size and isinstance(rows, list) and
            len(rows) <= limit and all(isinstance(r, dict) for r in rows), "news_page_shape_invalid")
    if provider == "marketaux":
        require(total >= (page - 1) * limit + len(rows), "marketaux_count_mismatch")
        exhausted = page * limit >= total
        require(exhausted or len(rows) == limit, "marketaux_truncated_page")
    else:
        exhausted = not rows
    return rows, limit, total, exhausted


def article_identity(provider, row):
    identity = row.get("uuid") if provider == "marketaux" else row.get("link")
    require(isinstance(identity, str) and identity, "news_identity_missing")
    return identity


def article_time(provider, row):
    value = row.get("published_at" if provider == "marketaux" else "publishDate")
    require(isinstance(value, str), "news_publication_time_missing")
    # Marketaux documents all its timestamps as UTC, even if a suffix is absent.
    if provider == "marketaux" and datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None:
        value += "Z"
    return parse_instant(value).astimezone(timezone.utc)


def record(row, run, matcher, evidence, target):
    source = run.spec["source"]
    published = article_time(source, row)
    entities = row.get("companies" if source == "finlight" else "entities") or []
    require(isinstance(entities, list) and all(isinstance(e, dict) for e in entities), "news_entities_invalid")
    names = sorted({e["name"] for e in entities if isinstance(e.get("name"), str) and e["name"]})
    candidates, sectors = matcher.match(names)
    # Search hits establish candidates only, including absent provider entities.
    candidates = sorted(set(candidates) | set(target.get("company_ids", [])))
    candidate_sectors = sorted(set(sectors) | set(target["sector_ids"]))
    payload = {"provider_id": article_identity(source, row), "record_type": "news_article",
        "title": row.get("title"), "data": row, "company_names": names,
        "candidate_company_ids": candidates, "candidate_sector_ids": candidate_sectors,
        "discovery_target": target, "company_match_basis": "unverified_names_or_search_query",
        "date_basis": "article_publication", "source_evidence": list(evidence),
        "coverage_note": "Provider-indexed search results; candidates are not verified company/sector links. Current text and sentiment may be revised; historical availability is unestablished."}
    return seal_record({"document_type": "collected_record", "schema_version": "1.0",
        "source": source, "dataset": "news_articles", "source_record_id": payload["provider_id"],
        "source_record_id_basis": "provider" if source == "marketaux" else "documented_composite",
        "source_url": row.get("url" if source == "marketaux" else "link"),
        "universe_version": run.universe["universe_version"], "company_ids": [], "listing_ids": [],
        "product_ids": [], "person_ids": [], "entity_match_status": "unresolved",
        "event_at": {"value": published.isoformat(), "precision": "microsecond" if published.microsecond else "second", "source_timezone": "UTC"},
        "available_at": None, "source_updated_at": None, "ingested_at": now(),
        "availability_basis": "unknown", "availability_evidence": [], "run_id": run.run_id, "payload": payload})


def collect(store, settings, universe, taxonomy, config, provider, target, language,
            start, end, mode, client, max_pages=5, refresh=False, probe_history=False):
    require(provider in URLS and start < end and mode in {"historical", "daily"}, "invalid_news_scope")
    require(type(max_pages) is int and max_pages > 0, "invalid_page_budget")
    pc = config["providers"][provider]
    scope = {"target": target, "language": language, "query": query_text(provider, target["terms"]),
        "page_size": pc["page_size"], "history_start": pc["history_start"],
        "history_evidence": pc["history_evidence"], "configuration_hash": digest(config),
        "completion_basis": "exhausted_provider_search_not_global_news_census"}
    fulltext = provider in ('finlight', 'marketaux') and getattr(client, 'capture_full_text', False)
    if fulltext:
        from importlib import import_module
        content_module = import_module(provider + '_content')
        TEXT_VERSION = content_module.VERSION
        scope['full_text_pipeline_version'] = TEXT_VERSION
    spec = task_spec(provider, "news_articles", mode, instant(start), instant(end), scope,
        VERSION + ('-' + TEXT_VERSION if fulltext else ''), universe, taxonomy)
    write_json(store, f"manifests/configurations/news/{digest(config)}.json", config)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=not refresh, refresh=refresh)
    except AlreadyComplete as exc:
        return {"status": "complete", "already_complete": True, "manifest": str(exc)}
    try:
        history_known = bool(pc["history_start"] and pc["history_evidence"])
        if pc.get("historical_access") == "recent_only":
            recent_boundary = datetime.now(timezone.utc).date() - timedelta(days=pc["conservative_recent_days"])
            if start < recent_boundary:
                raise SourceIssue("provider_history_unavailable", True)
            history_known = True  # Only within this conservative recent window.
        if mode == "historical":
            if pc["history_start"] and start < date.fromisoformat(pc["history_start"]):
                reason = "history_before_observed_archive_boundary" if pc.get("historical_access") == "observed_archive" else "provider_history_unavailable"
                raise SourceIssue(reason, True)
            if not history_known and not probe_history:
                raise SourceIssue("history_entitlement_unverified", True)
        state = json.loads(run.cursor) if run.cursor else {"page": 1, "limit": None, "total": None, "previous_hash": None}
        matcher = CompanyMatcher(universe)
        seen = set()
        for page in run.state["pages"]:
            for batch in page["batches"]:
                seen.update(json.loads(line)["source_record_id"] for line in store.get(batch["key"]).body.splitlines())
        pages = 0
        # Revalidate the last committed page before resuming an offset-based API.
        if state["page"] > 1 and not run.exhausted:
            previous = client.page(parameters(provider, scope["query"], language, start, end, state["page"] - 1, pc["page_size"]))
            previous_rows, limit, total, _ = page_info(provider, previous, state["page"] - 1, pc["page_size"])
            require(digest(previous_rows) == state["previous_hash"] and limit == state["limit"] and total == state["total"], "news_source_changed_refresh_required")
        while not run.exhausted:
            if pages >= max_pages:
                raise SourceIssue("page_limit", True)
            if provider == "marketaux" and state["limit"] and (state["page"] - 1) * state["limit"] >= 20000:
                raise SourceIssue("news_result_cap_split_window_required", True)
            data = client.page(parameters(provider, scope["query"], language, start, end, state["page"], pc["page_size"]))
            rows, limit, total, exhausted = page_info(provider, data, state["page"], pc["page_size"])
            require(state["limit"] in (None, limit) and state["total"] in (None, total), "news_source_changed_refresh_required")
            identities = [article_identity(provider, row) for row in rows]
            require(len(identities) == len(set(identities)) and not seen.intersection(identities), "news_duplicate_page_refresh_required")
            if state["page"] > 1 and rows:
                require(digest(rows) != state["previous_hash"], "news_repeated_page")
            # Keep out-of-range evidence but reject silently ignored date filters.
            stamps = [article_time(provider, row) for row in rows]
            lower = datetime.combine(start, datetime.min.time(), timezone.utc)
            upper = datetime.combine(end, datetime.min.time(), timezone.utc)
            require(all(lower - timedelta(seconds=1) <= stamp <= upper for stamp in stamps), "news_date_filter_ignored")
            records = []
            listing_evidence = list(client.evidence)
            for row, stamp in zip(rows, stamps):
                if lower <= stamp < upper:
                    result = record(row, run, matcher, listing_evidence, target)
                    if fulltext:
                        Capture, apply = content_module.Capture, content_module.apply
                        if not hasattr(client, 'fulltext_capture'):
                            client.fulltext_capture = Capture(store, client)
                        try:
                            capture = client.fulltext_capture.get(row, historical=mode == 'historical')
                        except SourceIssue as exc:
                            if not exc.partial:
                                raise
                            # Discovery must not lose an article because body
                            # retrieval used its budget. The content backfill
                            # will pick up this committed pending observation.
                            capture = {'version': TEXT_VERSION, 'status': 'pending', 'article_url': row['link'] if provider == 'finlight' else row['url'],
                                'captured_at': now(), 'source_evidence': [], 'text_characters': 0, 'reason': exc.code}
                        result = apply(result, capture, store)
                    records.append(result)
            # Persist even empty response evidence with the run for coverage audits.
            write_json(store, run.state["manifest_prefix"] + f"/responses/{len(run.state['pages']):08d}.json",
                {"parameters": parameters(provider, scope["query"], language, start, end, state["page"], pc["page_size"]),
                 "evidence": client.evidence, "returned": len(rows), "total": total, "exhausted": exhausted})
            state = {"page": state["page"] + 1, "limit": limit, "total": total, "previous_hash": digest(rows)}
            run.commit_page(records, next_cursor=None if exhausted else json.dumps(state, sort_keys=True), exhausted=exhausted)
            seen.update(identities)
            pages += 1
        if mode == "historical" and not history_known:
            raise SourceIssue("history_entitlement_unverified", True)
        return {"status": "complete", "records": run.state["record_count"],
                "manifest": run.finish("complete", expected_records=run.state["record_count"])}
    except (Exception, KeyboardInterrupt) as exc:
        return finish_error(run, exc, client.evidence)


def targets(config, universe, sectors, company_ids):
    selected = sectors or sorted(config["sector_terms"])
    require(set(selected) <= set(config["sector_terms"]), "unknown_news_sector")
    if not company_ids:
        return [{"name": sector, "sector_ids": [sector], "company_ids": [], "terms": config["sector_terms"][sector]} for sector in selected]
    companies = CompanyMatcher(universe, selected).companies
    require(set(company_ids) <= set(companies), "news_company_not_in_selected_universe")
    output = []
    for cid in sorted(set(company_ids)):
        company = companies[cid]
        names = [company["canonical_name"]] + [a["alias"] for a in universe["company_aliases"] if a["company_id"] == cid and a["review_status"] != "rejected"]
        output.append({"name": cid, "sector_ids": sorted({s["sector_id"] for s in company["sectors"] if s["review_status"] != "rejected"} & set(selected)),
            "company_ids": [cid], "terms": sorted(set(names)), "alias_time_basis": "current_registry_candidates_not_historical_identity"})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("daily", "historical"))
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat, help="exclusive end date")
    parser.add_argument("--provider", choices=tuple(URLS), action="append")
    parser.add_argument("--sector", action="append", default=[])
    parser.add_argument("--company-id", action="append", default=[])
    parser.add_argument("--language", help="single provider-supported language")
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--max-tasks", type=int, default=12)
    parser.add_argument("--max-requests", type=int, default=12, help="per provider, counting HTTP retries")
    parser.add_argument("--probe-history", action="store_true", help="bounded retrieval without claiming historical coverage")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config", type=Path, default=ROOT / "config/news-collection.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    today = datetime.now(timezone.utc).date()
    start = args.start or (historical_start() if args.mode == "historical" else today - timedelta(days=1))
    end = args.end or (today if args.mode == "daily" else None)
    if end is None or not start < end <= today or min(args.max_pages, args.max_tasks, args.max_requests) <= 0:
        parser.error("require start < end <= today and positive limits; historical requires --end")
    config = load_json(args.config)
    universe, taxonomy = load_json(ROOT / config["universe"]), load_json(ROOT / config["taxonomy"])
    selected = targets(config, universe, args.sector, args.company_id)
    providers = sorted(set(args.provider or URLS))
    jobs, cursor = [], start
    while cursor < end:
        following = following_window(cursor, end, args.mode)
        for provider in providers:
            languages = [args.language] if args.language else config["providers"][provider]["languages"]
            for target in selected:
                for language in languages:
                    jobs.append((provider, target, language, cursor, following))
        cursor = following
    if args.dry_run:
        print(json.dumps({"status": "planned", "start": str(start), "end_exclusive": str(end),
            "universe_version": universe["universe_version"], "sector_ids": sorted({s for t in selected for s in t["sector_ids"]}),
            "planned_tasks": len(jobs), "max_tasks": args.max_tasks, "max_requests_per_provider": args.max_requests,
            "providers": {p: config["providers"][p] for p in providers}, "targets": selected}, ensure_ascii=False))
        return 0
    with (ROOT / ".news-collection.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "partial", "reason": "news_runner_already_active"}))
            return 2
        import boto3
        secret = boto3.client("secretsmanager", region_name=config["region"]).get_secret_value(SecretId=config["secret_id"])
        keys = json.loads(secret["SecretString"])
        settings = StorageSettings.load(ROOT / config["storage_config"])
        store = settings.store()
        clients = {}
        for provider in providers:
            key = keys.get(config["providers"][provider]["secret_field"])
            require(isinstance(key, str) and key.strip(), "news_secret_field_missing")
            clients[provider] = NewsClient(store, provider, key.strip(), config["providers"][provider]["max_requests_per_day"], args.max_requests)
        results, attempted, blocked = [], 0, set()
        for provider, target, language, left, right in jobs:
            if attempted >= args.max_tasks:
                break
            if provider in blocked:
                continue
            result = collect(store, settings, universe, taxonomy, config, provider, target, language,
                left, right, args.mode, clients[provider], args.max_pages, args.refresh, args.probe_history)
            attempted += not result.get("already_complete", False)
            item = {"provider": provider, "target": target["name"], "language": language,
                "start": str(left), "end_exclusive": str(right), **result}
            results.append(item)
            print(json.dumps(item), flush=True)
            if result.get("reason") in {"news_provider_quota_or_rate_limit", "news_authentication_or_entitlement_denied", "run_request_budget_reached", "daily_request_budget_reached", "history_entitlement_unverified", "provider_history_unavailable", "history_before_observed_archive_boundary"}:
                # A history probe deliberately samples each selected target.
                if not (args.probe_history and result.get("reason") == "history_entitlement_unverified"):
                    blocked.add(provider)
        report = {"status": "complete" if len(results) == len(jobs) and all(r["status"] == "complete" for r in results) else "partial",
            "planned_tasks": len(jobs), "reported_tasks": len(results), "unattempted_tasks": len(jobs) - len(results),
            "results": results, "checked_at": now(), "athena_published": False}
        write_json(store, f"operations/news/runs/{uuid4()}.json", report)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(canonical_json(report) + b"\n")
        print(json.dumps({k: v for k, v in report.items() if k != "results"}), flush=True)
        return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
