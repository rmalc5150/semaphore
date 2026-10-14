#!/usr/bin/env python3
"""Schedule bounded USPTO catch-up; monitor global source metadata without paid queries."""
import argparse
from datetime import date, datetime, timedelta, timezone
import fcntl
import json
from pathlib import Path
from uuid import uuid4

from collection_operations import Operations, following_window, load_stored
from collection_storage import StorageSettings, now, write_json
import patent_collection as patent
from patent_bigquery_access import API, REQUIRED_FIELDS, response_json, session
from research_contract import ROOT, digest, load_json, validate_universe


class PatentOperations(Operations):
    def __init__(self, store, settings, config, universe, taxonomy, client=None):
        errors, _ = validate_universe(universe, taxonomy)
        if errors:
            raise ValueError("invalid patent universe")
        self.store, self.settings, self.config = store, settings, config
        self.universe, self.taxonomy, self.client = universe, taxonomy, client
        self.rules = load_json(patent.RULES_PATH)
        self.identity = digest({"version": "patent-operations-1.0", "universe": digest(universe),
            "taxonomy": digest(taxonomy), "collector": patent.VERSION,
            "rules": digest(self.rules), "page_size": config["page_size"]})
        self.prefix = f"operations/patents/streams/{self.identity}"
        self.force_refresh = False

    @staticmethod
    def boundary(source, day):
        return patent.instant(day)

    def completed(self, result, source, start, end, mode):
        if not result or result.get("status") != "complete" or not result.get("manifest"):
            return False
        manifest, _ = load_stored(self.store, result["manifest"])
        if not manifest:
            return False
        task = manifest["task"]
        task_id = "task_" + digest(task)
        head, _ = load_stored(self.store, f"checkpoints/{task_id}/head.json")
        scope = task["scope"]
        return bool(manifest["status"] == "complete" and manifest["exhausted"] and head and
            manifest["task_id"] == task_id and head["task"] == task and
            result["manifest"] in head["terminal_history"] and
            task["source"] == "uspto_odp" and task["dataset"] == "patent_records" and
            task["universe_hash"] == digest(self.universe) and task["taxonomy_hash"] == digest(self.taxonomy) and
            task["collector_version"] == patent.VERSION and task["mode"] == mode and
            task["window"] == {"start": patent.instant(start), "end": patent.instant(end)} and
            scope["classification_hash"] == digest(self.rules) and scope["page_size"] == self.config["page_size"] and
            scope["query"] == patent.search_query(start, end, mode, 0, self.config["page_size"])["q"])

    def window(self, source, start, end, mode, refresh=False):
        # Mutable USPTO counts cannot safely continue an old offset. Allow at
        # most one restart per cooldown per window, recording intent first.
        prior, _ = load_stored(self.store, self.outcome_key(source, start, end, mode))
        self.force_refresh = False
        if (prior and prior.get("reason") == "source_changed_refresh_required" and
                not (mode == 'daily' and self.config.get('daily_partition_strategy') == 'hourly-v1')):
            key = self.outcome_key(source, start, end, mode) + ".restart.json"
            receipt, token = load_stored(self.store, key)
            today = now()[:10]
            current = datetime.fromisoformat(now().replace('Z', '+00:00'))
            last = datetime.fromisoformat(receipt['started_at'].replace('Z', '+00:00')) if receipt else None
            cooldown = self.config.get('source_change_restart_hours', 24) * 3600
            if not receipt or (current-last).total_seconds() >= cooldown or receipt.get('max_pages', 0) < self.config['max_pages']:
                write_json(self.store, key, {"day": today, "prior_manifest": prior.get("manifest"),
                    "reason": "source_changed_refresh_required", "started_at": now(),
                    "max_pages": self.config['max_pages']}, token)
                self.force_refresh = True
            else:
                # Retrying a known-invalid offset cannot produce valid coverage.
                # Keep the original evidence while waiting for a fresh scan.
                return {**prior, 'retry_after': (last+timedelta(seconds=cooldown)).isoformat(),
                        'retry_deferred': True}
        try:
            return super().window(source, start, end, mode, refresh)
        finally:
            self.force_refresh = False

    def invoke(self, source, start, end, mode, inputs, refresh):
        if mode == 'daily' and self.config.get('daily_partition_strategy') == 'hourly-v1':
            return patent.collect_uspto_partitioned(self.store, self.settings, self.universe, self.taxonomy,
                start, end, page_size=self.config['page_size'], max_pages=self.config['max_pages'],
                refresh=refresh, client=self.client, rules=self.rules)
        return patent.collect_uspto(self.store, self.settings, self.universe, self.taxonomy,
            start, end, mode, page_size=self.config["page_size"], max_pages=self.config["max_pages"],
            refresh=refresh or self.force_refresh, client=self.client, rules=self.rules)

    def run(self, sources, mode, origin, end, max_windows, reconcile_days=0):
        if mode == "historical":
            return super().run(sources, mode, origin, end, max_windows)
        key = f"{self.prefix}/daily/uspto/progress-{origin}.json"
        progress, token = load_stored(self.store, key)
        cursor = date.fromisoformat(progress["next_date"]) if progress else origin
        results = []
        while cursor < end and len(results) < max_windows:
            following = following_window(cursor, end, "daily")
            result = self.window("uspto", cursor, following, "daily")
            results.append(result)
            if result["status"] != "complete":
                break
            cursor = following
            token = write_json(self.store, key, {"origin": str(origin), "next_date": str(cursor),
                "last_manifest": result["manifest"], "updated_at": now()}, token)
        if cursor >= end:
            recent = {str(end - timedelta(days=n)) for n in range(1, reconcile_days + 1)
                      if end - timedelta(days=n) >= origin}
            pending = self.pending_dates("uspto")
            for value in sorted(recent - pending):
                day = date.fromisoformat(value)
                prior, _ = load_stored(self.store, self.outcome_key("uspto", day, day + timedelta(days=1), "daily"))
                # An hourly timer must not repeatedly refresh the oldest day
                # and starve all newer reconciliation dates.
                if prior and prior.get("finished_at", "")[:10] == now()[:10] and self.completed(prior, "uspto", day, day + timedelta(days=1), "daily"):
                    continue
                self.set_pending("uspto", day, True)
                pending.add(value)
            for value in sorted(pending):
                if len(results) >= max_windows:
                    break
                day = date.fromisoformat(value)
                if day >= end:
                    continue
                result = self.window("uspto", day, day + timedelta(days=1), "daily", refresh=True)
                results.append(result)
                if result["status"] != "complete":
                    break
                self.set_pending("uspto", day, False)
        pending = sorted(self.pending_dates("uspto"))
        status = "complete" if cursor >= end and not pending and all(r["status"] == "complete" for r in results) else "partial"
        report = {"stream_id": self.identity, "mode": mode, "origin": str(origin),
            "end_exclusive": str(end), "finished_at": now(), "status": status,
            "sources": {"uspto": {"status": status, "next_date": str(cursor),
                "windows": results, "pending_reconciliation_dates": pending}}}
        receipt = f"operations/patents/reports/{uuid4()}.json"
        write_json(self.store, receipt, report)
        return {**report, "report_key": receipt}


def monitor_global(store, http):
    """Metadata GET only. Observing a revision never marks it collected."""
    table = response_json(http.get(API + "/projects/patents-public-data/datasets/patents/tables/publications", timeout=60))
    if REQUIRED_FIELDS - {f["name"] for f in table["schema"]["fields"]}:
        raise ValueError("global patent schema changed")
    metadata = {k: table.get(k) for k in ("id", "lastModifiedTime", "numRows", "numBytes")}
    if not metadata["id"] or not metadata["lastModifiedTime"]:
        raise ValueError("missing global source revision")
    key = "operations/patents/global-source/latest-observation.json"
    prior, token = load_stored(store, key)
    revision = digest(metadata)
    report = {"checked_at": now(), "revision": revision, "source_metadata": metadata,
        "changed_since_previous_observation": None if not prior else prior["revision"] != revision,
        "collection_status": "not_scheduled", "data_query_executed": False,
        "coverage_note": "Metadata observations do not establish publication freshness or completed collection."}
    receipt = f"operations/patents/global-source/observations/{digest(report)}.json"
    write_json(store, receipt, report)
    write_json(store, key, {**report, "receipt": receipt}, token)
    return {**report, "receipt": receipt}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("daily", "historical", "monitor-global"))
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat, help="exclusive end, default today UTC")
    parser.add_argument("--config", type=Path, default=ROOT / "config/patent-operations.json")
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--max-windows", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--backend", choices=("local", "s3"))
    parser.add_argument("--output-root")
    args = parser.parse_args(argv)
    config = load_json(args.config)
    if config.get('daily_partition_strategy') not in (None, 'hourly-v1'):
        parser.error('unsupported daily_partition_strategy')
    for field, override in (("max_pages", args.max_pages), ("max_windows", args.max_windows)):
        if override is not None:
            config[field] = override
        if type(config[field]) is not int or config[field] < 1:
            parser.error(field + " must be positive")
    if not 1 <= config["page_size"] <= 100:
        parser.error("page_size must be between 1 and 100")
    if type(config["reconcile_days"]) is not int or config["reconcile_days"] < 0:
        parser.error("reconcile_days must be a nonnegative integer")
    settings = StorageSettings.load(ROOT / config["storage_config"],
        {"backend": args.backend, "local_root": args.output_root})
    today = datetime.now(timezone.utc).date()
    end = args.end or today
    if args.mode == "daily":
        origin = date.fromisoformat(config["daily_origin"])
        if args.start:
            parser.error("daily origin is pinned in config; use a separate config for a separate stream")
    elif args.mode == "historical":
        from historical_policy import historical_start
        if not args.end:
            parser.error("historical requires explicit --end; --start defaults to the shared historical start")
        origin = args.start or historical_start()
    else:
        if args.start or args.end or args.status:
            parser.error("monitor-global accepts no date range or --status")
        origin = end
    if end > today or (args.mode != "monitor-global" and origin > end) or (args.mode == "historical" and origin == end):
        parser.error("only completed days can be collected")
    universe = load_json(ROOT / config["universe"])
    taxonomy = load_json(ROOT / config["taxonomy"])
    operations = PatentOperations(None, settings, config, universe, taxonomy)
    if args.dry_run:
        print(json.dumps({"status": "planned", "mode": args.mode, "origin": str(origin),
            "end_exclusive": str(end), "stream_id": operations.identity,
            "universe_version": universe["universe_version"], "page_size": config["page_size"],
            "max_pages_per_window": config["max_pages"], "max_windows": config["max_windows"],
            "daily_partition_strategy": config.get('daily_partition_strategy'),
            "athena_publication": "separate_reviewed_release", "global_queries": "not_scheduled"}, indent=2))
        return 0
    lock_name = ".patent-global-monitor.lock" if args.mode == "monitor-global" else ".patent-operations.lock"
    with (ROOT / lock_name).open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "partial", "reason": "runner_already_active"}))
            return 2
        store = settings.store()
        if args.mode == "monitor-global":
            with session(ROOT / config["credentials"]) as http:
                report = monitor_global(store, http)
        else:
            operations.store = store
            report = (operations.status(["uspto"], args.mode, origin, end) if args.status else
                operations.run(["uspto"], args.mode, origin, end, config["max_windows"],
                    config["reconcile_days"] if args.mode == "daily" else 0))
        print(json.dumps(report), flush=True)
        if any(r["status"] == "failed" for source in report.get("sources", {}).values() for r in source.get("windows", [])):
            return 1
        return 0 if args.status or args.mode == "monitor-global" or report["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
