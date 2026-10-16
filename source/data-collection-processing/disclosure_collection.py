#!/usr/bin/env python3
"""Resumable HKEX disclosures and dependency-checked disclosure processing."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import sys
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from collection_storage import (AlreadyComplete, CollectionRun, Conflict, StorageSettings,
    advance_watermark, now, read_watermark, task_spec, write_json)
from regulatory_collection import CompanyMatcher, EvidenceClient, SourceIssue, require
from research_contract import ROOT, digest, load_json, parse_instant, seal_record, validate_record
from disclosure_content import VERSION as CONTENT_VERSION

VERSION = "disclosures-1.1"
HKEX_API = "https://www1.hkexnews.hk/search/titleSearchServlet.do"
SECTORS = ("biotech", "robotics", "semiconductors", "energy_storage")
CATEGORIES = ("press-releases", "licensing-agreements", "ma-announcements", "strategic-transactions")
SEC_DOCUMENT_FORMS = ("8-K", "8-K/A", "6-K", "6-K/A", "10-K", "10-K/A", "10-Q", "10-Q/A", "S-4", "S-4/A", "425", "DEFM14A", "SC 13D", "SC 13D/A")
ZONES = {"sec_edgar": "America/New_York", "hkex_news": "Asia/Hong_Kong"}


def midnight(day, zone="UTC"):
    return datetime.combine(day, datetime.min.time(), ZoneInfo(zone)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def get_bytes(store, key, checksum=None):
    obj = store.get(key)
    require(obj is not None, "missing_prerequisite_object")
    require(checksum is None or hashlib.sha256(obj.body).hexdigest() == checksum, "prerequisite_checksum_mismatch")
    return obj.body


def read_inputs(store, keys, universe, taxonomy):
    """Validate immutable, committed, complete inputs; never scan raw prefixes."""
    require(keys, "prerequisite_manifests_required")
    records, inputs, manifests = {}, [], []
    verified_evidence = set()
    for key in sorted(set(keys)):
        raw = get_bytes(store, key)
        manifest = json.loads(raw)
        task = manifest["task"]
        require(manifest["status"] == "complete" and manifest["exhausted"], "prerequisite_not_complete")
        task_id = "task_" + digest(task)
        require(task_id == manifest["task_id"], "prerequisite_task_mismatch")
        head = json.loads(get_bytes(store, f"checkpoints/{task_id}/head.json"))
        require(head["task"] == task and key in head["terminal_history"], "prerequisite_not_committed")
        require(task["universe_hash"] == digest(universe) and task["taxonomy_hash"] == digest(taxonomy), "prerequisite_configuration_mismatch")
        require((task["source"], task["dataset"]) in {
            ("sec_edgar", "filings"), ("hkex_news", "filings"), ("disclosure_documents", "documents"),
            *(("disclosure_candidates", category.replace("-", "_")) for category in CATEGORIES)}, "unsupported_prerequisite")
        # The SEC-specific reader additionally checks issuer rows against the
        # pinned quarterly index, including inherited pages.
        if task["source"] == "sec_edgar":
            from sec_athena_pilot import read_inputs as read_sec
            read_sec(store, [key])
        count, seen = 0, set()
        for page in manifest["pages"]:
            page_count = 0
            for batch in page["batches"]:
                body = get_bytes(store, batch["key"], batch["sha256"])
                rows = [json.loads(line) for line in body.splitlines()]
                require(len(body) == batch["bytes"] and len(rows) == batch["records"], "prerequisite_batch_mismatch")
                for record in rows:
                    require(not validate_record(record, universe), "invalid_prerequisite_record")
                    require(record["source"] == task["source"] and record["dataset"] == task["dataset"] and
                            record["run_id"] == page["run_id"], "prerequisite_record_scope_mismatch")
                    require(record["observation_id"] not in seen, "duplicate_prerequisite_observation")
                    seen.add(record["observation_id"])
                    if task["source"] != "sec_edgar":
                        require(record["payload"].get("source_evidence"), "prerequisite_evidence_missing")
                        for ref in record["payload"]["source_evidence"]:
                            pair = (ref['key'], ref['sha256'])
                            if pair not in verified_evidence:
                                get_bytes(store, ref["key"], ref["sha256"])
                                verified_evidence.add(pair)
                    identity = record["record_id"]
                    entry = {"record": record, "manifest": key, "batch": batch["key"], "batch_sha256": batch["sha256"]}
                    if identity not in records or (record["ingested_at"], record["observation_id"]) > (
                            records[identity]["record"]["ingested_at"], records[identity]["record"]["observation_id"]):
                        records[identity] = entry
                page_count += len(rows)
            require(page_count == page["record_count"], "prerequisite_page_count_mismatch")
            count += page_count
        require(count == manifest["record_count"] == manifest["expected_records"], "prerequisite_count_mismatch")
        inputs.append({"key": key, "sha256": hashlib.sha256(raw).hexdigest(), "records": count})
        manifests.append(manifest)
    return [records[key] for key in sorted(records)], inputs, manifests


def check_coverage(manifests, start, end, required_sources):
    require(required_sources, "required_sources_missing")
    require({m["task"]["source"] for m in manifests} == set(required_sources), "prerequisite_source_set_mismatch")
    for source in required_sources:
        intervals = []
        for manifest in manifests:
            task = manifest["task"]
            if task["source"] != source:
                continue
            zone = ZoneInfo(ZONES.get(source, "UTC"))
            bounds = [parse_instant(task["window"][key]).astimezone(zone) for key in ("start", "end")]
            require(all(t.hour == t.minute == t.second == 0 for t in bounds), "prerequisite_calendar_boundary_mismatch")
            intervals.append(tuple(t.date() for t in bounds))
        cursor = start
        for left, right in sorted(intervals):
            if left > cursor:
                break
            cursor = max(cursor, right)
        require(cursor >= end, "prerequisite_window_gap")


def make_record(run, identity, payload, event_date, url, parent=None, names=(), evidence=(), timezone_name=None):
    matcher = CompanyMatcher(run.universe, run.spec["scope"].get("sectors", []))
    candidates, sectors = matcher.match(names)
    confirmed = parent["company_ids"] if parent else []
    if parent:
        candidates = sorted(set(candidates) | set(parent["payload"].get("candidate_company_ids", [])))
    candidates = sorted(set(candidates) - set(confirmed))
    payload = {**payload, "company_names": list(names), "candidate_company_ids": candidates,
               "candidate_sector_ids": sectors, "source_evidence": list(evidence)}
    return seal_record({"document_type": "collected_record", "schema_version": "1.0",
        "source": run.spec["source"], "dataset": run.spec["dataset"], "source_record_id": identity,
        "source_record_id_basis": "provider" if run.spec["source"] == "hkex_news" else "documented_composite",
        "source_url": url, "universe_version": run.universe["universe_version"],
        "company_ids": confirmed, "listing_ids": [], "product_ids": [], "person_ids": [],
        "entity_match_status": parent["entity_match_status"] if parent else "unresolved",
        "event_at": {"value": event_date, "precision": "day", "source_timezone": timezone_name},
        "source_updated_at": None, "available_at": None, "availability_basis": "unknown", "availability_evidence": [],
        "ingested_at": now(), "run_id": run.run_id, "payload": payload})


def keep(record, selection, sectors, universe):
    if selection == "all":
        return True
    ids = set(record["company_ids"]) | set(record["payload"]["candidate_company_ids"])
    eligible = {c["company_id"] for c in universe["companies"] if c["collection_enabled"] and c["review_status"] != "rejected"
        and (not sectors or any(s["sector_id"] in sectors and s["review_status"] != "rejected" for s in c["sectors"]))}
    return bool(ids & eligible)


def finish_error(run, exc, evidence=()):
    if isinstance(exc, Conflict):
        raise exc
    code = exc.code if isinstance(exc, SourceIssue) else "interrupted" if isinstance(exc, KeyboardInterrupt) else "collection_error"
    status = "partial" if isinstance(exc, KeyboardInterrupt) or (isinstance(exc, SourceIssue) and exc.partial) else "failed"
    write_json(run.store, run.state["manifest_prefix"] + "/failure.json", {
        "reason": code, "error_type": type(exc).__name__, "evidence": list(evidence), "cursor": run.cursor})
    return {"status": status, "reason": code, "manifest": run.finish(status, code)}


def hkex_page(client, day, state, page_size, stock_id=""):
    loaded = state.get("loaded", 0)
    params = {"sortDir": "0", "sortByOptions": "DateTime", "category": "0", "market": "SEHK",
        "stockId": stock_id, "documentType": "", "fromDate": day.strftime("%Y%m%d"), "toDate": day.strftime("%Y%m%d"),
        "title": "", "searchType": "0", "t1code": "-2", "t2Gcode": "-2", "t2code": "-2",
        "rowRange": loaded + page_size, "lang": "EN"}
    data = client.json(HKEX_API, params=params)
    try:
        rows = json.loads(data["result"]) if isinstance(data["result"], str) else data["result"]
        total, returned = int(data["recordCnt"]), int(data["loadedRecord"])
    except (ValueError, TypeError, KeyError):
        raise SourceIssue("hkex_invalid_response") from None
    require(isinstance(rows, list) and returned == len(rows) and 0 <= returned <= total, "hkex_count_mismatch")
    require(type(data.get("hasNextRow")) is bool and data["hasNextRow"] == (returned < total), "hkex_completion_unverified")
    require(state.get("total", total) == total, "source_changed_during_pagination")
    require(not loaded or digest(rows[:loaded]) == state["prefix_hash"], "hkex_prefix_changed")
    if returned <= loaded and returned < total:
        raise SourceIssue("hkex_result_limit_or_no_progress", True)
    ids = [str(row.get("NEWS_ID", "")) for row in rows]
    require(all(re.fullmatch(r"\d+", value) for value in ids) and len(ids) == len(set(ids)), "hkex_invalid_or_duplicate_identity")
    for row in rows:
        try:
            published = datetime.strptime(row["DATE_TIME"], "%d/%m/%Y %H:%M")
        except (ValueError, KeyError):
            raise SourceIssue("hkex_publication_date_missing") from None
        require(published.date() == day, "hkex_date_filter_ignored")
        url = urljoin(HKEX_API, row.get("FILE_LINK", ""))
        require(urlsplit(url).scheme == "https" and urlsplit(url).hostname == "www1.hkexnews.hk"
                and urlsplit(url).path.startswith("/listedco/"), "hkex_document_link_invalid")
    return rows[loaded:], {"loaded": returned, "total": total, "prefix_hash": digest(rows)}, returned == total


def collect_hkex(store, settings, universe, taxonomy, start, end, mode, selection="all", sectors=(),
                 stock_id="", page_size=100, max_pages=None, refresh=False, client=None, capture_documents=True):
    scope = {"selection": selection, "sectors": sorted(set(sectors)), "stock_id": stock_id,
             "market": "SEHK", "language": "EN", "page_size": page_size, "date_basis": "hkex_release_date",
             "document_capture": "original_bytes_v1" if capture_documents else "metadata_only"}
    spec = task_spec("hkex_news", "filings", mode, midnight(start, "Asia/Hong_Kong"), midnight(end, "Asia/Hong_Kong"), scope, VERSION, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=not refresh, refresh=refresh)
    except AlreadyComplete as exc:
        return {"status": "complete", "manifest": str(exc), "already_complete": True}
    client = client or EvidenceClient(store, "hkex_news")
    try:
        state = json.loads(run.cursor) if run.cursor else {"day": str(start)}
        pages = 0
        while not run.exhausted:
            if max_pages is not None and pages >= max_pages:
                return {"status": "partial", "reason": "page_limit", "manifest": run.finish("partial", "page_limit")}
            day = date.fromisoformat(state["day"])
            client.evidence = []
            rows, following, done = hkex_page(client, day, state, page_size, stock_id)
            search_evidence = list(client.evidence)
            records = []
            for row in rows:
                payload = {"record_type": "disclosure", "title": row["TITLE"], "data": row, "date_basis": "hkex_release_date",
                    "release_time": datetime.strptime(row["DATE_TIME"], "%d/%m/%Y %H:%M").replace(tzinfo=ZoneInfo("Asia/Hong_Kong")).isoformat(),
                    "coverage_note": "English HKEX SEHK search metadata within the configured date, stock and universe scope; current observations, not reconstructed historical versions."}
                record = make_record(run, str(row["NEWS_ID"]), payload, str(day), urljoin(HKEX_API, row["FILE_LINK"]),
                                     names=[row["STOCK_NAME"]], evidence=search_evidence, timezone_name="Asia/Hong_Kong")
                if keep(record, selection, sectors, universe):
                    if capture_documents:
                        client.evidence = []
                        from disclosure_document_cache import lookup, remember
                        saved = lookup(store, record['source_url']) if mode == 'historical' else None
                        if saved:
                            raw, ref = saved
                            client.evidence = [ref]
                        else:
                            raw = client.get(record["source_url"])
                        if row.get("FILE_TYPE", "").upper() == "PDF":
                            require(raw.startswith(b"%PDF-"), "hkex_non_pdf_response")
                        else:
                            document_text(raw, record)
                        require(bool(client.evidence), "hkex_document_evidence_missing")
                        remember(store, client.evidence[0])
                        payload["document_capture"] = {"status": "captured", "bytes": len(raw),
                            "source_evidence": list(client.evidence)}
                        payload["coverage_note"] = "English HKEX SEHK search metadata and original linked documents within the configured scope; text extraction is a separate stage; current observations, not reconstructed historical versions."
                        record = make_record(run, str(row["NEWS_ID"]), payload, str(day), record["source_url"],
                            names=[row["STOCK_NAME"]], evidence=search_evidence + list(client.evidence), timezone_name="Asia/Hong_Kong")
                    records.append(record)
            client.evidence = search_evidence
            next_day = day + timedelta(days=1)
            exhausted = done and next_day == end
            following = {"day": str(next_day)} if done else {"day": str(day), **following}
            write_json(store, run.state["manifest_prefix"] + f"/inputs/{len(run.state['pages']):08d}.json", {
                "cursor_before": state, "cursor_after": following, "source_ids": [str(row["NEWS_ID"]) for row in rows], "evidence": client.evidence})
            run.commit_page(records, next_cursor=None if exhausted else json.dumps(following, sort_keys=True), exhausted=exhausted)
            state, pages = following, pages + 1
        return {"status": "complete", "records": run.state["record_count"], "manifest": run.finish("complete", expected_records=run.state["record_count"])}
    except (Exception, KeyboardInterrupt) as exc:
        return finish_error(run, exc, client.evidence)


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head", "ix:hidden"):
            self.hidden += 1
        if tag in ("p", "div", "br", "tr", "td", "li"):
            self.parts.append(" ")
    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "ix:hidden"):
            self.hidden = max(0, self.hidden - 1)
        self.parts.append(" ")
    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def visible_text(text):
    parser = VisibleText()
    parser.feed(text)
    return " ".join("".join(parser.parts).split())


def document_text(raw, parent):
    from disclosure_content import extract
    content = extract(raw, parent)
    return content['text'], content['extraction']


def candidate(category, parent):
    from corporate_disclosures import EVENT_RULES
    text = parent["payload"]["data"]["text"]
    if category == "strategic-transactions":
        from strategic_transactions import CATEGORY_RULES
        patterns = [(name, pattern) for name, (pattern, _) in CATEGORY_RULES.items()]
    else:
        patterns = [(word, re.escape(word)) for word in EVENT_RULES[category]["keywords"]]
        chinese = {"press-releases": ("新聞稿", "新闻稿", "業績公告", "业绩公告"),
                   "licensing-agreements": ("許可協議", "许可协议", "授權協議", "授权协议"),
                   "ma-announcements": ("收購", "收购", "合併", "合并", "要約", "要约")}
        patterns += [(word, re.escape(word)) for word in chinese[category]]
    matches = []
    for term, pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            start, end = max(0, match.start()-200), min(len(text), match.end()+300)
            span = next((s for s in parent['payload']['data'].get('document_spans', [])
                         if s['start'] <= match.start() < s['end']), None)
            if span:
                start, end = max(start, span['start']), min(end, span['end'])
            excerpt = text[start:end]
            from disclosure_content import signals
            matches.append({"term": term, "excerpt": excerpt, 'start': start, 'end': end,
                'match_start': match.start(), 'match_end': match.end(), 'document': span,
                'context_signals': signals(excerpt)})
    return matches


def collect_derived(store, settings, universe, taxonomy, start, end, mode, stage, manifest_keys,
                    required_sources, selection="all", sectors=(), max_records=None, refresh=False, client=None,
                    sec_forms=SEC_DOCUMENT_FORMS):
    entries, inputs, manifests = read_inputs(store, manifest_keys, universe, taxonomy)
    check_coverage(manifests, start, end, required_sources)
    expected = {"sec_edgar", "hkex_news"} if stage == "documents" else {"disclosure_documents"}
    require(set(required_sources) <= expected, "wrong_prerequisite_stage")
    entries = [entry for entry in entries if start.isoformat() <= entry["record"]["event_at"]["value"][:10] < end.isoformat()]
    if stage == "documents":
        entries = [entry for entry in entries if entry["record"]["source"] != "sec_edgar" or
            set(entry['record']['payload'].get('index_forms', [entry['record']['payload']['form']])).intersection(sec_forms)]
    source, dataset = ("disclosure_documents", "documents") if stage == "documents" else ("disclosure_candidates", stage.replace("-", "_"))
    scope = {"inputs": inputs, "required_sources": sorted(set(required_sources)), "selection": selection,
             "sectors": sorted(set(sectors)), "date_basis": "parent_source_calendar_date",
             "coverage": "Only the explicit completed prerequisite scopes; full source content preserved; passage-supported candidates are unreviewed, not confirmed corporate events.",
             'content_pipeline_version': CONTENT_VERSION}
    if stage == "documents":
        scope["sec_forms"] = sorted(set(sec_forms))
    spec = task_spec(source, dataset, mode, midnight(start), midnight(end), scope, VERSION + '-' + CONTENT_VERSION, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=not refresh, refresh=refresh)
    except AlreadyComplete as exc:
        return {"status": "complete", "manifest": str(exc), "already_complete": True}
    client = client or EvidenceClient(store, source)
    try:
        offset = int(run.cursor or 0)
        require(0 <= offset <= len(entries), "invalid_derived_cursor")
        processed = 0
        if not entries and not run.exhausted:
            run.commit_page([], exhausted=True)
        while not run.exhausted and offset < len(entries):
            if max_records is not None and processed >= max_records:
                return {"status": "partial", "reason": "record_limit", "manifest": run.finish("partial", "record_limit")}
            entry = entries[offset]
            parent = entry["record"]
            client.evidence = []
            names = parent["payload"].get("company_names", [r["company_name"] for r in parent["payload"].get("issuer_rows", [])])
            lineage = {"manifest": entry["manifest"], "batch": entry["batch"], "batch_sha256": entry["batch_sha256"],
                       "record_id": parent["record_id"], "observation_id": parent["observation_id"]}
            identity = parent["source"] + ":" + parent["source_record_id"]
            payload = {"title": parent["payload"].get("title") or parent["payload"].get("form"),
                "form": parent["payload"].get("form"), "origin_source": parent["payload"].get("origin_source", parent["source"]),
                "prerequisite": lineage, "date_basis": parent["payload"].get("date_basis", "sec_filing_date"), "coverage_note": scope["coverage"]}
            if parent['payload'].get('index_forms'):
                payload['index_forms'] = parent['payload']['index_forms']
            accepted = keep({**parent, "payload": {**parent["payload"], "candidate_company_ids": parent["payload"].get("candidate_company_ids", [])}}, selection, sectors, universe)
            matches = None
            if accepted and stage == "documents":
                url = parent["source_url"]
                host = "www.sec.gov" if parent["source"] == "sec_edgar" else "www1.hkexnews.hk"
                require(urlsplit(url).scheme == "https" and urlsplit(url).hostname == host, "unapproved_document_host")
                captured = parent["payload"].get("document_capture")
                if captured and captured.get("status") == "captured":
                    refs = captured["source_evidence"]
                    require(len(refs) == 1 and refs[0]["source_url"] == url, "document_capture_reference_invalid")
                    raw = get_bytes(store, refs[0]["key"], refs[0]["sha256"])
                    require(len(raw) == captured["bytes"], "document_capture_size_mismatch")
                    client.evidence = list(refs)
                else:
                    from disclosure_document_cache import lookup
                    saved = lookup(store, url) if mode == 'historical' else None
                    if saved:
                        raw, ref = saved
                        client.evidence = [ref]
                    else:
                        raw = client.get(url)
                from disclosure_document_cache import remember
                for ref in client.evidence:
                    if ref['source_url'] == url:
                        remember(store, ref)
                from disclosure_content import extract, persist
                content = extract(raw, parent)
                reference = persist(store, content, url)
                client.evidence.append(reference)
                payload.update(record_type="disclosure_document", content_reference=reference,
                    content_pipeline_version=CONTENT_VERSION, data={"text": content['text'] if len(content['text'].encode()) <= 1024 * 1024 else None,
                    'text_storage': 'full_content_reference', 'full_content_reference': reference, "extraction": content['extraction'],
                    'document_spans': content['document_spans'], 'text_sha256': content['text_sha256'],
                    'chunk_count': len(content['chunks']), 'textless_pdf_pages': content['textless_pdf_pages']})
            elif accepted:
                reference = parent['payload'].get('content_reference')
                require(reference is not None and reference.get('content_version') == CONTENT_VERSION,
                        'full_content_prerequisite_required')
                content = json.loads(get_bytes(store, reference['key'], reference['sha256']))
                inline = parent['payload']['data']['text']
                require(inline is None or content['text'] == inline, 'full_content_text_mismatch')
                parent_for_matching = {**parent, 'payload': {**parent['payload'], 'data': {
                    **parent['payload']['data'], 'text': content['text']}}}
                matches = candidate(stage, parent_for_matching)
                for match in matches:
                    span = match['document']
                    match['chunk_ids'] = [c['chunk_id'] for c in content['chunks'] if span and
                        c['document_id'] == span['document_id'] and
                        c['start'] < match['end'] - span['start'] and c['end'] > match['start'] - span['start']]
                payload.update(content_reference=reference, content_pipeline_version=CONTENT_VERSION)
                payload.update(record_type="event_candidate", data={"category": stage, "review_status": "unreviewed",
                    "classification_basis": "source_text_passages", "matches": matches,
                    'full_content_reference': reference, 'form_hint': parent['payload'].get('form'),
                    'event_status': 'requires_review', 'entity_link_status': parent['entity_match_status'],
                    "note": "May describe proposed, historical, negated or unrelated events; terms, completion and economics are not confirmed."})
            records = []
            if accepted and (stage == "documents" or matches):
                evidence = client.evidence if stage == "documents" else parent["payload"]["source_evidence"]
                records = [make_record(run, identity, payload, parent["event_at"]["value"][:10], parent["source_url"],
                                      parent, names, evidence, parent["event_at"].get("source_timezone"))]
            offset, processed = offset + 1, processed + 1
            run.commit_page(records, next_cursor=str(offset) if offset < len(entries) else None, exhausted=offset == len(entries))
        return {"status": "complete", "records": run.state["record_count"], "manifest": run.finish("complete", expected_records=run.state["record_count"])}
    except (Exception, KeyboardInterrupt) as exc:
        return finish_error(run, exc, client.evidence)


def main(stage, argv=None):
    from historical_policy import add_end_option, resolve_dates
    parser = argparse.ArgumentParser(description=__doc__)
    add_end_option(parser)
    parser.add_argument("mode", choices=("daily", "historical"))
    parser.add_argument("start", nargs="?", type=date.fromisoformat)
    parser.add_argument("end", nargs="?", type=date.fromisoformat)
    parser.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    parser.add_argument("--backend", choices=("s3", "local"))
    parser.add_argument("--output-root")
    from research_contract import COLLECTION_UNIVERSE
    parser.add_argument("--universe", type=Path, default=COLLECTION_UNIVERSE)
    parser.add_argument("--taxonomy", type=Path, default=ROOT / "config/sectors.v1.json")
    parser.add_argument("--selection", choices=("all", "universe"), default="all")
    parser.add_argument("--sector", action="append", choices=SECTORS, default=[])
    parser.add_argument("--source-manifest", action="append", default=[])
    parser.add_argument("--require-source", action="append", choices=("sec_edgar", "hkex_news", "disclosure_documents"))
    parser.add_argument("--hkex-stock-id", default="")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--max-records", type=int)
    parser.add_argument("--lookback-days", type=int, default=0)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--sec-form", action="append", default=[], help="document stage only; explicit SEC form scope")
    args = parser.parse_args(argv)
    resolve_dates(parser, args, args.mode)
    today = datetime.now(timezone.utc).date()
    if args.mode == "historical":
        if args.start is None or args.end is None:
            parser.error("historical requires START END; END is exclusive")
        start, end = args.start, args.end
    else:
        if args.end:
            parser.error("daily accepts one date")
        end = (args.start or today - timedelta(days=1)) + timedelta(days=1)
        start = end - timedelta(days=1 + args.lookback_days)
    if start >= end or end > today or args.lookback_days < 0:
        parser.error("use completed source-calendar days and nonnegative lookback")
    if args.sector and args.selection != "universe":
        parser.error("--sector requires --selection universe")
    if not 1 <= args.page_size <= 1000 or any(value is not None and value < 1 for value in (args.max_pages, args.max_records)):
        parser.error("invalid page or record limit")
    if args.hkex_stock_id and not args.hkex_stock_id.isdigit():
        parser.error("HKEX stock ID must be numeric; it is not the exchange ticker")
    if args.sec_form and stage != "documents":
        parser.error("--sec-form applies only to document collection")
    if stage == "hkex" and (args.source_manifest or args.require_source or args.max_records):
        parser.error("HKEX accepts --max-pages, not prerequisite or derived-record options")
    if stage != "hkex" and (not args.source_manifest or args.hkex_stock_id or args.max_pages):
        parser.error("derived collectors require --source-manifest and accept --max-records instead of --max-pages")
    settings = StorageSettings.load(args.storage_config, {"backend": args.backend, "local_root": args.output_root})
    store = settings.store()
    universe, taxonomy = load_json(args.universe), load_json(args.taxonomy)
    try:
        if stage == "hkex":
            result = collect_hkex(store, settings, universe, taxonomy, start, end, args.mode, args.selection,
                args.sector, args.hkex_stock_id, args.page_size, args.max_pages, args.refresh)
        else:
            required = args.require_source or (["sec_edgar", "hkex_news"] if stage == "documents" else ["disclosure_documents"])
            result = collect_derived(store, settings, universe, taxonomy, start, end, args.mode, stage,
                args.source_manifest, required, args.selection, args.sector, args.max_records, args.refresh,
                sec_forms=tuple(args.sec_form) or SEC_DOCUMENT_FORMS)
        if result["status"] == "complete":
            manifest = json.loads(get_bytes(store, result["manifest"]))
            previous = read_watermark(store, manifest["task"])
            try:
                result["completed_until"] = advance_watermark(store, result["manifest"], previous["origin"] if previous else manifest["task"]["window"]["start"])["completed_until"]
            except ValueError:
                result["watermark_status"] = "coverage_gap_not_advanced"
        print(json.dumps({"stage": stage, "start": str(start), "end": str(end), **result}), flush=True)
        return 0 if result["status"] == "complete" else 2
    except Exception as exc:
        print(json.dumps({"status": "failed", "reason": exc.code if isinstance(exc, SourceIssue) else "pipeline_error", "error_type": type(exc).__name__}), flush=True)
        return 2


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("hkex", "documents", *CATEGORIES):
        raise SystemExit("usage: disclosure_collection.py {hkex,documents,press-releases,licensing-agreements,ma-announcements,strategic-transactions} ...")
    raise SystemExit(main(sys.argv[1], sys.argv[2:]))
