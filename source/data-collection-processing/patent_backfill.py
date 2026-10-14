#!/usr/bin/env python3
"""Bounded global patent backfill with durable monthly progress and query reservations."""
import argparse
from datetime import date, datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from collection_operations import load_stored, following_window
from collection_storage import StorageSettings, now, write_json
from historical_policy import historical_start
from patent_bigquery_access import API, PROJECT, response_json, session, verify
from patent_bigquery_collection import BigQuery, collect, query_scope
from patent_collection import RULES_PATH, VERSION, SourceIssue, instant, require, collection_task
from patent_query_plan import build
from research_contract import ROOT, digest, load_json, validate_universe

PREFIX = "operations/patents/global-backfill"


class BudgetedBigQuery(BigQuery):
    def __init__(self, http, store, config, plan):
        super().__init__(http)
        self.store, self.config, self.plan = store, config, plan

    def reserve(self, identity):
        maximum = self.config["maximum_bytes_billed"]
        day = now()[:10]
        key = f"{PREFIX}/budgets/{day}.json"
        budget, token = load_stored(self.store, key)
        jobs = dict(budget["jobs"]) if budget else {}
        if identity not in jobs:
            if len(jobs) >= self.config["max_new_jobs_per_day"] or sum(jobs.values()) + maximum > self.config["max_reserved_bytes_per_day"]:
                raise SourceIssue("daily_query_budget_reached", True)
            jobs[identity] = maximum
            write_json(self.store, key, {"day": day, "jobs": jobs, "updated_at": now()}, token)
        return key

    def authorize(self, identity, query):
        key = f"{PREFIX}/jobs/{identity}.json"
        authorization, _ = load_stored(self.store, key)
        if authorization:
            require(authorization["query_hash"] == digest(query), "job_authorization_mismatch")
            age = datetime.now(timezone.utc) - datetime.fromisoformat(authorization["authorized_at"].replace("Z", "+00:00"))
            require(age.total_seconds() < 20 * 3600, "missing_old_job_manual_review_required")
            # A prior-day request with an ambiguous submission outcome still
            # consumes today's reservation if it must be submitted today.
            self.reserve(identity)
            return
        estimate = verify(self.http, self.plan)
        if not estimate["estimate_within_ceiling"]:
            raise SourceIssue("estimated_scan_exceeds_ceiling", True)
        require(estimate["location"] == "US", "unexpected_source_location")
        maximum = self.config["maximum_bytes_billed"]
        require(int(query["maximumBytesBilled"]) == maximum, "query_ceiling_mismatch")
        budget_key = self.reserve(identity)
        # Reserve before submission. Crash-orphaned reservations count toward
        # the cap; never reclaim potentially spent capacity automatically.
        write_json(self.store, key, {"job_id": identity, "authorized_at": now(),
            "query_hash": digest(query), "query_plan_hash": digest(self.plan),
            "budget_key": budget_key, "estimate": estimate})

    def job(self, identity, query):
        url = API + f"/projects/{PROJECT}/jobs/{identity}"
        response = self.http.get(url, params={"location": "US"}, timeout=60)
        if response.status_code == 404:
            self.authorize(identity, query)
            # Retry uses the collector's already-committed job identity.
            response = self.http.post(API + f"/projects/{PROJECT}/jobs", json={
                "jobReference": {"projectId": PROJECT, "location": "US", "jobId": identity},
                "configuration": {"query": query}}, timeout=60)
            if response.status_code == 409:
                response = self.http.get(url, params={"location": "US"}, timeout=60)
        job = response_json(response)
        require(all(job["configuration"]["query"].get(k) == v for k, v in query.items()), "existing_job_configuration_mismatch")
        return job

    def page(self, identity, token, size):
        params = {"location": "US", "maxResults": size, "timeoutMs": 10000}
        if token:
            params["pageToken"] = token
        response = self.http.get(API + f"/projects/{PROJECT}/queries/{identity}", params=params, timeout=60)
        require(response.status_code not in {404, 410}, "query_results_unavailable_manual_review_required")
        return response_json(response)


class Backfill:
    def __init__(self, store, settings, config, universe, taxonomy):
        errors, _ = validate_universe(universe, taxonomy)
        if errors:
            raise ValueError("invalid universe")
        self.store, self.settings, self.config = store, settings, config
        self.universe, self.taxonomy = universe, taxonomy
        self.start = date.fromisoformat(config["start_date"]) if "start_date" in config else historical_start()
        self.end = date.fromisoformat(config["end_exclusive"])
        if self.start.day != 1:
            raise ValueError("patent backfill must start on the first of a month")
        if self.start >= self.end or self.end > datetime.now(timezone.utc).date():
            raise ValueError("invalid completed-day historical range")
        for field in ("maximum_bytes_billed", "max_pages", "max_new_jobs_per_day", "max_reserved_bytes_per_day"):
            if type(config[field]) is not int or config[field] <= 0:
                raise ValueError("positive integer required: " + field)
        if type(config["page_size"]) is not int or not 1 <= config["page_size"] <= 1000:
            raise ValueError("invalid page_size")
        self.rules = load_json(RULES_PATH)
        self.identity = digest({"version": "patent-backfill-1.0", "start": str(self.start), "end": str(self.end),
            "universe": digest(universe), "taxonomy": digest(taxonomy), "rules": digest(self.rules),
            "collector": VERSION, "sql": digest((ROOT / "patent_discovery.sql").read_text()),
            "maximum_bytes_billed": config["maximum_bytes_billed"], "page_size": config["page_size"]})
        self.prefix = f"{PREFIX}/streams/{self.identity}"
        self.progress_key = self.prefix + "/progress.json"

    def status(self):
        progress, _ = load_stored(self.store, self.progress_key)
        return {"stream_id": self.identity, "start": str(self.start), "end_exclusive": str(self.end),
            "universe_version": self.universe["universe_version"], "athena_publication": "separate_reviewed_release",
            **(progress or {"next_date": str(self.start), "completed_windows": 0, "status": "not_started"})}

    def completed(self, result, plan):
        require(result.get("manifest"), "completion_manifest_missing")
        manifest, _ = load_stored(self.store, result["manifest"])
        require(manifest is not None, "completion_manifest_missing")
        task = manifest["task"]
        task_id = "task_" + digest(task)
        head, _ = load_stored(self.store, f"checkpoints/{task_id}/head.json")
        scope = task["scope"]
        p = plan["provenance"]
        require(manifest["status"] == "complete" and manifest["exhausted"] and head and
            manifest["task_id"] == task_id and head["task"] == task and result["manifest"] in head["terminal_history"] and
            task["source"] == "google_patents_bigquery" and task["dataset"] == "patent_records" and
            task["mode"] == "historical" and task["collector_version"] == VERSION and
            task["universe_hash"] == digest(self.universe) and task["taxonomy_hash"] == digest(self.taxonomy) and
            task["window"] == {"start": instant(date.fromisoformat(p["window_start"])), "end": instant(date.fromisoformat(p["window_end_exclusive"]))} and
            scope["query_plan_hash"] == digest(plan) and scope["page_size"] == self.config["page_size"] and
            scope["maximum_bytes_billed"] == self.config["maximum_bytes_billed"], "completion_manifest_mismatch")
        return manifest["record_count"]

    def completed_window(self, start):
        """Read one committed month without a provider call or collection mutation."""
        progress, _ = load_stored(self.store, self.progress_key)
        end = following_window(start, self.end, "historical")
        require(self.start <= start < end <= self.end and start.day == 1,
                "invalid_publication_window")
        if not progress or end > date.fromisoformat(progress["next_date"]):
            return None
        plan = build(self.universe, self.rules, start, end, self.config["maximum_bytes_billed"])
        scope = query_scope(plan, self.config["maximum_bytes_billed"], self.config["page_size"])
        task = collection_task(self.universe, self.taxonomy, "google_patents_bigquery",
            start, end, "historical", scope, self.rules)
        head, _ = load_stored(self.store, "checkpoints/task_" + digest(task) + "/head.json")
        require(head is not None and head["status"] == "complete" and head["task"] == task,
                "completed_window_checkpoint_missing_or_changed")
        result = {"manifest": head["terminal_manifest"], "start": str(start), "end_exclusive": str(end)}
        result["records"] = self.completed(result, plan)
        result["manifest_sha256"] = hashlib.sha256(self.store.get(result["manifest"]).body).hexdigest()
        return result

    def audit(self):
        progress, _ = load_stored(self.store, self.progress_key)
        result = (progress or {}).get("last_complete")
        if not result and (progress or {}).get("last_attempt", {}).get("status") == "complete":
            result = progress["last_attempt"]
        require(result is not None, "no_complete_window_to_audit")
        plan, _ = load_stored(self.store, f"{self.prefix}/plans/{result['plan_hash']}.json")
        expected = self.completed(result, plan)
        manifest, _ = load_stored(self.store, result["manifest"])
        observations, evidence, authorities = set(), {}, {}
        count = batches = 0
        for page in manifest["pages"]:
            page_count = 0
            for batch in page["batches"]:
                obj = self.store.get(batch["key"])
                require(obj is not None and hashlib.sha256(obj.body).hexdigest() == batch["sha256"], "raw_batch_hash_mismatch")
                lines = obj.body.splitlines()
                require(len(lines) == batch["records"], "raw_batch_count_mismatch")
                batches += 1
                for line in lines:
                    record = json.loads(line)
                    require(record["observation_id"] not in observations, "duplicate_observation")
                    observations.add(record["observation_id"])
                    data = record["payload"]["data"]
                    require(result["start"] <= data["publication_date"] < result["end_exclusive"], "raw_publication_outside_window")
                    country = data.get("country_code") or "unknown"
                    authorities[country] = authorities.get(country, 0) + 1
                    for ref in record["payload"]["source_evidence"]:
                        require(ref["key"] not in evidence or evidence[ref["key"]] == ref["sha256"], "conflicting_evidence_hash")
                        evidence[ref["key"]] = ref["sha256"]
                page_count += len(lines)
            require(page_count == page["record_count"], "raw_page_count_mismatch")
            count += page_count
        require(count == expected, "raw_total_mismatch")
        for key, checksum in evidence.items():
            obj = self.store.get(key)
            require(obj is not None and hashlib.sha256(obj.body).hexdigest() == checksum, "source_evidence_hash_mismatch")
        initial = json.loads(manifest["pages"][0]["cursor_after"])
        export, _ = load_stored(self.store, f"incoming/patents/google-bigquery/{initial['export_date']}/{initial['job_id']}/export-metadata.json")
        require(export is not None and export["row_count"] == count and export["query_plan_hash"] == digest(plan), "export_metadata_mismatch")
        report = {"status": "verified", "checked_at": now(), "stream_id": self.identity,
            "manifest": result["manifest"], "start": result["start"], "end_exclusive": result["end_exclusive"],
            "records": count, "batches_verified": batches, "evidence_objects_verified": len(evidence),
            "authorities": authorities, "job_id": initial["job_id"],
            "total_bytes_billed": export["statistics"].get("query", {}).get("totalBytesBilled"),
            "athena_published": False, "review_status": "candidates_require_review"}
        key = f"{self.prefix}/audits/{digest(report)}.json"
        write_json(self.store, key, report)
        return {**report, "audit_key": key}

    def run(self, http, client=None):
        progress, token = load_stored(self.store, self.progress_key)
        cursor = date.fromisoformat(progress["next_date"]) if progress else self.start
        require(self.start <= cursor <= self.end, "invalid_progress_date")
        if cursor == self.end:
            return self.status()
        following = following_window(cursor, self.end, "historical")
        plan = build(self.universe, self.rules, cursor, following, self.config["maximum_bytes_billed"])
        write_json(self.store, f"{self.prefix}/plans/{digest(plan)}.json", plan)
        attempt = {"started_at": now(), "start": str(cursor), "end_exclusive": str(following), "plan_hash": digest(plan)}
        try:
            result = collect(self.store, self.settings, self.universe, self.taxonomy, plan,
                self.config["maximum_bytes_billed"], client or BudgetedBigQuery(http, self.store, self.config, plan),
                page_size=self.config["page_size"], max_pages=self.config["max_pages"])
            if result["status"] == "complete":
                result["records"] = self.completed(result, plan)
        except Exception as exc:
            result = {"status": "failed", "reason": getattr(exc, "code", "backfill_exception"), "error_type": type(exc).__name__}
        result = {**attempt, **{k: v for k, v in result.items() if k != "statistics"}, "finished_at": now()}
        receipt = f"{self.prefix}/attempts/{uuid4()}.json"
        write_json(self.store, receipt, result)
        done = result["status"] == "complete"
        last_complete = (progress or {}).get("last_complete")
        if not last_complete and (progress or {}).get("last_attempt", {}).get("status") == "complete":
            last_complete = progress["last_attempt"]
        value = {"next_date": str(following if done else cursor),
            "last_complete": result if done else last_complete,
            "completed_windows": (progress or {}).get("completed_windows", 0) + int(done),
            "completed_records": (progress or {}).get("completed_records", 0) + (result["records"] if done else 0),
            "status": "complete" if done and following == self.end else "in_progress" if done else result["status"],
            "last_attempt": result, "last_attempt_key": receipt, "updated_at": now()}
        write_json(self.store, self.progress_key, value, token)
        return self.status()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/patent-backfill.json")
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--audit", action="store_true", help="read back and hash-check the most recent complete window")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_json(args.config)
    if args.max_pages is not None:
        config["max_pages"] = args.max_pages
    settings = StorageSettings.load(ROOT / config["storage_config"])
    runner = Backfill(None, settings, config, load_json(ROOT / config["universe"]), load_json(ROOT / config["taxonomy"]))
    if args.dry_run:
        print(json.dumps({"status": "planned", "stream_id": runner.identity, "start": str(runner.start),
            "end_exclusive": str(runner.end), "universe_version": runner.universe["universe_version"], **config}, indent=2))
        return 0
    with (ROOT / ".patent-backfill.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "partial", "reason": "runner_already_active"}))
            return 2
        runner.store = settings.store()
        if args.audit:
            report = runner.audit()
        elif args.status:
            report = runner.status()
        else:
            with session(ROOT / config["credentials"]) as http:
                report = runner.run(http)
        print(json.dumps(report), flush=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
        return 0 if args.status or args.audit or report["status"] == "complete" else 1 if report["status"] == "failed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
