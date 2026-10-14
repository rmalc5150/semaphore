#!/usr/bin/env python3
"""Run migrated collectors with durable date progress and explicit dependencies.

Daily dates are tracked independently per source. Historical dates use exact,
exclusive bounds and monthly windows. This runner does not publish Athena.
"""
from datetime import date, datetime, timedelta, timezone
import argparse
import fcntl
import json
from pathlib import Path
from uuid import uuid4

from collection_storage import StorageSettings, now, write_json
from research_contract import ROOT, digest, load_json, validate_universe
import regulatory_collection as regulatory
from regulatory_sources import ADAPTERS
import disclosure_collection as disclosure
import sec_filings as sec

VERSION = "collection-operations-1.0"
ORDER = ("sec", "clinicaltrials", "fda", "ema", "uk", "japan", "chictr",
         "hkex-filings", "documents", *disclosure.CATEGORIES)
DEPENDENCIES = {"documents": ("sec", "hkex-filings"),
                **{name: ("documents",) for name in disclosure.CATEGORIES}}
SOURCE_IDS = {name: adapter.source for name, adapter in ADAPTERS.items()}
SOURCE_IDS.update({"sec": "sec_edgar", "hkex-filings": "hkex_news",
    "documents": "disclosure_documents",
    **{name: "disclosure_candidates" for name in disclosure.CATEGORIES}})


def selected_sources(names):
    selected = set(names)
    if selected - set(ORDER):
        raise ValueError("not migrated in this runner: " + ", ".join(sorted(selected - set(ORDER))))
    for name in reversed(ORDER):
        if name in selected:
            selected.update(DEPENDENCIES.get(name, ()))
    return [name for name in ORDER if name in selected]


def following_window(start, end, mode):
    following = (start + timedelta(days=1) if mode == "daily" else
        date(start.year + (start.month == 12), start.month % 12 + 1, 1))
    return min(following, end)


def load_stored(store, key):
    obj = store.get(key)
    return (json.loads(obj.body), obj.token) if obj else (None, None)


class Operations:
    def __init__(self, store, settings, config, universe, taxonomy):
        errors, _ = validate_universe(universe, taxonomy)
        if errors:
            raise ValueError("invalid collection universe")
        self.store, self.settings, self.config = store, settings, config
        self.universe, self.taxonomy = universe, taxonomy
        self.cache = {}
        self.selection, self.sectors = config["selection"], config.get("sectors", [])
        if self.selection not in {"all", "universe"} or (self.sectors and self.selection != "universe"):
            raise ValueError("sectors require selection=universe")
        self.identity = digest({"version": VERSION, "universe": digest(universe),
            "taxonomy": digest(taxonomy), "selection": self.selection,
            "document_selection": config.get("document_selection", "universe"),
            "sectors": sorted(self.sectors),
            "versions": [sec.VERSION, regulatory.VERSION, disclosure.VERSION],
            "dependencies": DEPENDENCIES})
        self.prefix = f"operations/streams/{self.identity}"

    def outcome_key(self, source, start, end, mode):
        return f"{self.prefix}/{mode}/{source}/{start}_{end}.json"

    def pending_dates(self, source):
        value, _ = load_stored(self.store, f"{self.prefix}/daily/{source}/reconciliation.json")
        return set(value["pending_dates"]) if value else set()

    def status(self, sources, mode, origin, end):
        rows = {}
        for source in sources:
            suffix = str(origin) if mode == "daily" else f"{origin}_{end}"
            progress, _ = load_stored(self.store, f"{self.prefix}/{mode}/{source}/progress-{suffix}.json")
            cursor = date.fromisoformat(progress["next_date"]) if progress else origin
            pending = sorted(self.pending_dates(source)) if mode == "daily" else []
            check_day = date.fromisoformat(pending[0]) if pending else cursor
            latest, _ = load_stored(self.store, self.outcome_key(source, check_day,
                following_window(check_day, max(end, check_day + timedelta(days=1)), mode), mode))
            manifest_key = latest.get("manifest") if latest else None
            manifest_key = manifest_key or (progress.get("last_manifest") if progress else None)
            manifest, _ = load_stored(self.store, manifest_key) if manifest_key else (None, None)
            rows[source] = {"next_date": str(cursor), "pending_reconciliation_dates": pending,
                "status": latest["status"] if latest else "caught_up" if cursor >= end and not pending else "not_started",
                "reason": latest.get("reason") if latest else None,
                "manifest": manifest_key, "manifest_record_count": manifest.get("record_count") if manifest else None}
        return {"stream_id": self.identity, "checked_at": now(), "mode": mode,
            "universe_version": self.universe["universe_version"], "sources": rows,
            "not_scheduled": self.config.get("not_scheduled"), "separate_jobs": self.config.get("separate_jobs")}

    def set_pending(self, source, day, pending):
        key = f"{self.prefix}/daily/{source}/reconciliation.json"
        value, token = load_stored(self.store, key)
        dates = set(value["pending_dates"]) if value else set()
        dates.add(str(day)) if pending else dates.discard(str(day))
        write_json(self.store, key, {"pending_dates": sorted(dates), "updated_at": now()}, token)

    @staticmethod
    def boundary(source, day):
        if source == "sec":
            return sec.midnight(day)
        if source == "hkex-filings":
            return disclosure.midnight(day, "Asia/Hong_Kong")
        return regulatory.instant(day)

    def completed(self, result, source, start, end, mode):
        if not result or result.get("status") != "complete" or not result.get("manifest"):
            return False
        manifest, _ = load_stored(self.store, result["manifest"])
        if not manifest:
            return False
        task = manifest["task"]
        task_id = "task_" + digest(task)
        head, _ = load_stored(self.store, f"checkpoints/{task_id}/head.json")
        dataset = ("filings" if source in {"sec", "hkex-filings"} else "documents"
            if source == "documents" else source.replace("-", "_")
            if source in disclosure.CATEGORIES else "research_records")
        return bool(manifest["status"] == "complete" and manifest["exhausted"] and head and
            manifest["task_id"] == task_id and head["task"] == task and
            result["manifest"] in head["terminal_history"] and
            task["universe_hash"] == digest(self.universe) and
            task["taxonomy_hash"] == digest(self.taxonomy) and task["mode"] == mode and
            task["source"] == SOURCE_IDS[source] and task["dataset"] == dataset and
            task["window"]["start"] == self.boundary(source, start) and
            task["window"]["end"] == self.boundary(source, end))

    def invoke(self, source, start, end, mode, inputs, refresh):
        args = (self.store, self.settings, self.universe, self.taxonomy)
        if source == "sec":
            matcher = sec.CompanyMatcher(self.universe, sectors=self.sectors)
            scope = {"selection": self.selection, "company_ids": sorted(matcher.companies),
                "sectors": sorted(set(self.sectors)), "ciks": [], "forms": [],
                "date_basis": "filing_date_america_new_york"}
            return sec.collect_window(*args, sec.SECClient(self.config["sec_user_agent"]),
                start, end, mode, scope, matcher, self.cache,
                refresh=refresh, max_records=self.config.get("sec_max_records", self.config["max_records"]))
        if source == "hkex-filings":
            return disclosure.collect_hkex(*args, start, end, mode,
                self.selection, self.sectors, max_pages=self.config["max_pages"], refresh=refresh)
        if source in DEPENDENCIES:
            return disclosure.collect_derived(*args, start, end, mode, source, inputs,
                [SOURCE_IDS[name] for name in DEPENDENCIES[source]],
                selection=self.config.get("document_selection", "universe"), sectors=self.sectors,
                max_records=self.config["max_records"], refresh=refresh)
        return regulatory.collect(*args, source, start, end, mode, ADAPTERS[source](),
            selection=self.selection, sectors=self.sectors,
            max_pages=self.config["max_pages"], refresh=refresh)

    def window(self, source, start, end, mode, refresh=False):
        key = self.outcome_key(source, start, end, mode)
        prior, token = load_stored(self.store, key)
        inputs = []
        for parent in DEPENDENCIES.get(source, ()):
            result, _ = load_stored(self.store, self.outcome_key(parent, start, end, mode))
            if not self.completed(result, parent, start, end, mode):
                result = {"status": "blocked", "reason": "prerequisite_incomplete",
                    "prerequisite": parent, "source": source, "start": str(start),
                    "end": str(end), "mode": mode, "finished_at": now()}
                write_json(self.store, key, result, token)
                return result
            inputs.append(result["manifest"])
        if (not refresh and self.completed(prior, source, start, end, mode) and
                prior.get("inputs", []) == inputs):
            return {**prior, "already_complete": True}
        # A killed refresh attempt must resume its pages on the next invocation.
        refresh = refresh and bool(prior and prior.get("status") == "complete")
        attempt = {"source": source, "start": str(start), "end": str(end),
                   "mode": mode, "inputs": inputs, "status": "running", "started_at": now()}
        token = write_json(self.store, key, attempt, token)
        try:
            result = self.invoke(source, start, end, mode, inputs, refresh)
            if result.get("status") == "complete" and not self.completed(result, source, start, end, mode):
                raise ValueError("collector completion has no matching committed manifest")
        except Exception as exc:
            result = {"status": "failed", "reason": "collector_exception", "error_type": type(exc).__name__}
        result = {**attempt, **{k: v for k, v in result.items() if k != "task"}, "finished_at": now()}
        receipt = f"operations/attempts/{uuid4()}.json"
        write_json(self.store, receipt, result)
        result["attempt_receipt"] = receipt
        write_json(self.store, key, result, token)
        if mode == "daily" and result["status"] == "complete":
            for child, parents in DEPENDENCIES.items():
                if source in parents:
                    previous, _ = load_stored(self.store, self.outcome_key(child, start, end, mode))
                    if previous and result["manifest"] not in previous.get("inputs", []):
                        self.set_pending(child, start, True)
        return result

    def run(self, sources, mode, origin, end, max_windows, reconcile_days=0):
        report = {"stream_id": self.identity, "mode": mode, "origin": str(origin),
                  "end_exclusive": str(end), "sources": {}, "started_at": now()}
        for source in sources:
            # Historical end is part of progress identity: extending a partial
            # month must not make a derived window lose its parent boundaries.
            suffix = str(origin) if mode == "daily" else f"{origin}_{end}"
            progress_key = f"{self.prefix}/{mode}/{source}/progress-{suffix}.json"
            progress, token = load_stored(self.store, progress_key)
            cursor = date.fromisoformat(progress["next_date"]) if progress else origin
            results, attempted = [], 0
            while cursor < end and attempted < max_windows:
                following = following_window(cursor, end, mode)
                result = self.window(source, cursor, following, mode)
                results.append({"start": str(cursor), "end": str(following), **result})
                attempted += 1
                print(json.dumps({"source": source, "start": str(cursor), "status": result["status"],
                    "manifest": result.get("manifest"), "reason": result.get("reason")}), flush=True)
                if result["status"] != "complete":
                    break
                cursor = following
                token = write_json(self.store, progress_key,
                    {"next_date": str(cursor), "origin": str(origin),
                     "last_manifest": result["manifest"], "updated_at": now()}, token)
            if mode == "daily" and cursor >= end:
                recent = {str(end - timedelta(days=n)) for n in range(1, reconcile_days + 1)
                          if end - timedelta(days=n) >= origin}
                dates = sorted(self.pending_dates(source) | recent)
                for value in dates:
                    day = date.fromisoformat(value)
                    if day >= end or attempted >= max_windows:
                        break
                    if not any(r["start"] == str(day) for r in results):
                        self.set_pending(source, day, True)
                        result = self.window(source, day, day + timedelta(days=1), mode, refresh=True)
                        results.append({"start": str(day), "end": str(day + timedelta(days=1)), **result})
                        attempted += 1
                        if result["status"] != "complete":
                            break
                    self.set_pending(source, day, False)
            pending = sorted(self.pending_dates(source)) if mode == "daily" else []
            report["sources"][source] = {"next_date": str(cursor), "windows": results,
                "pending_reconciliation_dates": pending,
                "status": "complete" if cursor >= end and not pending and all(r["status"] == "complete" for r in results) else "partial"}
        report["status"] = "complete" if all(r["status"] == "complete" for r in report["sources"].values()) else "partial"
        report["finished_at"] = now()
        key = f"operations/reports/{uuid4()}.json"
        write_json(self.store, key, report)
        return {**report, "report_key": key}


def universe_windows(config, mode, origin, end, reconcile_days=0):
    """Route new daily windows without rewriting prior universe checkpoints.

    Historical runs remain explicitly pinned to config.universe. Older daily
    epochs keep their original progress origin and drain pending reconciliation.
    """
    if mode != "daily":
        return [{"universe": config["universe"], "origin": origin, "end": end, "reconcile_days": 0}]
    epochs = config.get("daily_universe_epochs", [])
    dates = [date.fromisoformat(e["effective_from"]) for e in epochs]
    if dates != sorted(set(dates)) or any(d <= date.fromisoformat(config["daily_origin"]) for d in dates):
        raise ValueError("Universe epochs must be unique, ordered and after the original daily origin")
    current, cursor, result = config["universe"], origin, []
    for epoch, boundary in zip(epochs, dates):
        if boundary <= origin:
            current = epoch["universe"]
            continue
        if boundary >= end:
            break
        result.append({"universe": current, "origin": cursor, "end": boundary,
            "reconcile_days": max(0, reconcile_days - (end - boundary).days)})
        current, cursor = epoch["universe"], boundary
    result.append({"universe": current, "origin": cursor, "end": end, "reconcile_days": reconcile_days})
    return result


def main(mode, argv=None):
    from historical_policy import add_end_option, resolve_dates
    p = argparse.ArgumentParser(description=__doc__)
    add_end_option(p)
    p.add_argument("start", nargs="?", type=date.fromisoformat,
        help="daily inclusive end date, or historical inclusive start")
    p.add_argument("end", nargs="?", type=date.fromisoformat, help="historical exclusive end")
    p.add_argument("--config", type=Path, default=ROOT / "config/collection-operations.json")
    p.add_argument("--only", action="append", choices=ORDER)
    p.add_argument("--origin", type=date.fromisoformat, help="initial daily date; keep fixed for catch-up")
    p.add_argument("--max-windows", type=int)
    p.add_argument("--max-pages", type=int)
    p.add_argument("--max-records", type=int)
    p.add_argument("--reconcile-days", type=int, default=0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--status", action="store_true", help="read S3 progress without fetching provider data")
    p.add_argument("--backend", choices=("local", "s3"))
    p.add_argument("--output-root")
    args = p.parse_args(argv)
    resolve_dates(p, args, mode)
    config = load_json(args.config)
    for flag, field in ((args.max_pages, "max_pages"), (args.max_records, "max_records"),
                        (args.max_windows, "max_windows_per_source")):
        if flag is not None:
            config[field] = flag
        if config[field] < 1:
            p.error(field + " must be positive")
    if args.reconcile_days < 0 or (mode == "historical" and args.reconcile_days):
        p.error("reconciliation requires daily mode and a nonnegative day count")
    today = min(datetime.now(timezone.utc).date(), datetime.now(sec.NY).date())
    if mode == "daily":
        if args.end:
            p.error("daily accepts one date")
        origin = args.origin or date.fromisoformat(config["daily_origin"])
        end = args.start + timedelta(days=1) if args.start else today
    else:
        if args.start is None or args.end is None:
            p.error("historical requires START END (YYYY-MM-DD, end exclusive)")
        origin, end = args.start, args.end
    if origin >= end or end > today:
        p.error("use a nonempty range of completed days")
    sources = selected_sources(args.only or config["sources"])
    if "sec" in sources and origin < date(1994, 7, 1):
        p.error("SEC quarterly-index collection begins 1994-07-01; select other sources for earlier dates")
    try:
        windows = universe_windows(config, mode, origin, end, args.reconcile_days)
    except ValueError as exc:
        p.error(str(exc))
    taxonomy = load_json(ROOT / config["taxonomy"])
    universes = {w["universe"]: load_json(ROOT / w["universe"]) for w in windows}
    for universe in universes.values():
        errors, _ = validate_universe(universe, taxonomy)
        if errors:
            p.error("invalid universe: " + errors[0])
    universe = universes[windows[-1]["universe"]]
    settings = StorageSettings.load(ROOT / config["storage_config"],
        {"backend": args.backend, "local_root": args.output_root})
    if args.dry_run:
        print(json.dumps({"status": "planned", "mode": mode, "origin": str(origin),
            "end_exclusive": str(end), "sources_in_dependency_order": sources,
            "universe_version": universe["universe_version"], "selection": config["selection"],
            "universe_windows": [{**w, "origin": str(w["origin"]), "end": str(w["end"]),
                "universe_version": universes[w["universe"]]["universe_version"]} for w in windows],
            "max_windows_per_source": config["max_windows_per_source"],
            "max_pages": config["max_pages"], "max_records": config["max_records"],
            "sec_max_records": config.get("sec_max_records"),
            "document_selection": config.get("document_selection"),
            "backend": settings.backend, "not_scheduled": config.get("not_scheduled"),
            "separate_jobs": config.get("separate_jobs")}, indent=2))
        return 0
    if args.status:
        store = settings.store()
        reports = [Operations(store, settings, config, universes[w["universe"]], taxonomy).status(sources, mode, w["origin"], w["end"]) for w in windows]
        print(json.dumps(reports[0] if len(reports) == 1 else {"universe_epochs": reports}, indent=2))
        return 0
    with (ROOT / ".collection-operations.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "partial", "reason": "runner_already_active"}))
            return 2
        store = settings.store()
        reports = []
        for window in windows:
            operations = Operations(store, settings, config, universes[window["universe"]], taxonomy)
            reports.append(operations.run(sources, mode, window["origin"], window["end"],
                config["max_windows_per_source"], window["reconcile_days"]))
        if len(reports) > 1:
            status = "complete" if all(r["status"] == "complete" for r in reports) else "partial"
            print(json.dumps({"status": status, "universe_epochs": reports}), flush=True)
            return 0 if status == "complete" else 2
        report = reports[0]
    print(json.dumps({"status": report["status"], "report_key": report["report_key"],
        "sources": {name: {"status": value["status"], "next_date": value["next_date"]}
                    for name, value in report["sources"].items()}}), flush=True)
    return 0 if report["status"] == "complete" else 2
