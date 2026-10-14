#!/usr/bin/env python3
"""Publish completed historical patent months, independently of raw collection."""
import argparse
from datetime import date
import fcntl
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from collection_operations import load_stored
from collection_storage import StorageSettings, now, write_json
from patent_backfill import Backfill
import patent_backfill_athena as curated
from research_contract import ROOT, canonical_json, digest, load_json


class Publisher:
    def __init__(self, backfill, config, output_root):
        self.backfill = backfill
        self.store, self.settings = backfill.store, backfill.settings
        self.config, self.output_root = config, Path(output_root)
        self.prefix = backfill.prefix + "/athena-publication"
        self.progress_key = self.prefix + "/progress.json"
        # A changed policy/runtime must be reviewed instead of silently replacing
        # partitions or changing the release identity halfway through a retry.
        self.contract = {"version": "patent-backfill-publication-1.0",
            "stream_id": backfill.identity, "curator": curated.VERSION,
            "arrow": curated.pa.__version__, "schema_hash": digest(curated.SCHEMA),
            "policy_hash": digest(load_json(curated.POLICY_PATH)), "athena": config,
            "bucket": self.settings.s3_bucket, "s3_prefix": self.settings.s3_prefix}
        self.contract_hash = digest(self.contract)

    def state(self):
        value, token = load_stored(self.store, self.progress_key)
        if value:
            curated.release.require(value["contract_hash"] == self.contract_hash,
                                    "Publication contract changed; review before resuming")
        else:
            value = {"contract_hash": self.contract_hash, "contract": self.contract,
                "next_date": str(self.backfill.start), "verified_months": 0,
                "verified_publications": 0, "status": "not_started", "active": None}
        cursor = date.fromisoformat(value["next_date"])
        curated.release.require(self.backfill.start <= cursor <= self.backfill.end and
            (cursor == self.backfill.end or cursor.day == 1), "Invalid publication cursor")
        return value, token

    def save(self, state, token):
        state["updated_at"] = now()
        return write_json(self.store, self.progress_key, state, token)

    def status(self):
        state, _ = self.state()
        raw, _ = load_stored(self.store, self.backfill.progress_key)
        return {**state, "stream_id": self.backfill.identity,
            "collected_months": (raw or {}).get("completed_windows", 0),
            "pending_collected_months": max(0, (raw or {}).get("completed_windows", 0) - state["verified_months"]),
            "verified_until_exclusive": state["next_date"],
            "collected_until_exclusive": (raw or {}).get("next_date", str(self.backfill.start)),
            "publication_progress_key": self.progress_key}

    def receipt(self, key, candidate):
        receipt, _ = load_stored(self.store, key)
        if receipt:
            curated.release.require(receipt["contract_hash"] == self.contract_hash and
                receipt["source"] == candidate and receipt["status"] == "verified",
                "Publication receipt does not match completed month")
            obj = self.store.get(receipt["verification_key"])
            curated.release.require(obj is not None and
                hashlib.sha256(obj.body).hexdigest() == receipt["verification_sha256"],
                "Publication verification evidence missing or changed")
            verification = json.loads(obj.body)
            curated.release.require(verification["status"] == "verified" and
                verification["release_id"] == receipt["release_id"] and
                verification["publication_month"] == candidate["start"][:7],
                "Publication verification does not match receipt")
        return receipt

    def run(self, max_months=1):
        if type(max_months) is not int or not 1 <= max_months <= 4:
            raise ValueError("max_months must be between 1 and 4")
        state, token = self.state()
        stage = "discovering"
        try:
            for _ in range(max_months):
                cursor = date.fromisoformat(state["next_date"])
                if cursor == self.backfill.end:
                    state["status"] = "complete"
                    token = self.save(state, token)
                    break
                stage = "discovering"
                candidate = self.backfill.completed_window(cursor)
                if candidate is None:
                    state["status"] = "waiting_for_collection"
                    token = self.save(state, token)
                    break
                month = candidate["start"][:7]
                receipt_key = f"{self.prefix}/months/{month}.json"
                receipt = self.receipt(receipt_key, candidate)
                if not receipt:
                    active = state.get("active")
                    if active:
                        curated.release.require(active["source"] == candidate,
                                                "Pending publication input changed")
                    else:
                        active = {"source": candidate}
                        state["active"] = active
                    state["status"] = "running"
                    state.pop("last_error", None)
                    stage = active["stage"] = "preparing"
                    token = self.save(state, token)
                    root = self.output_root / active["release_id"] if active.get("release_id") else None
                    if root is None or not (root / "release.json").exists():
                        root = curated.prepare(self.store, self.settings, self.config,
                            candidate["manifest"], self.output_root)
                    report = load_json(root / "release.json")
                    curated.release.require(report["publication_month"] == month and
                        report["window_start"] == candidate["start"] and
                        report["window_end_exclusive"] == candidate["end_exclusive"] and
                        report["counts"]["publications"] == candidate["records"] and
                        report["inputs"] == [{"key": candidate["manifest"], "records": candidate["records"],
                                              "sha256": candidate["manifest_sha256"]}] and
                        report["policy_hash"] == self.contract["policy_hash"] and
                        report["config"] == self.config,
                        "Prepared release does not match publication task")
                    if active.get("release_id"):
                        curated.release.require(active["release_id"] == report["release_id"] and
                            active["report_hash"] == digest(report), "Prepared release changed during retry")
                    active.update(release_id=report["release_id"], report_hash=digest(report))
                    stage = active["stage"] = "uploading"
                    token = self.save(state, token)
                    curated.publish(self.store, self.settings, root)
                    stage = active["stage"] = "deploying_and_verifying"
                    token = self.save(state, token)
                    verification = curated.deploy(self.store, self.settings, root)
                    body = canonical_json(verification) + b"\n"
                    checksum = hashlib.sha256(body).hexdigest()
                    receipt = {"status": "verified", "contract_hash": self.contract_hash,
                        "source": candidate, "release_id": report["release_id"],
                        "verified_at": verification["checked_at"],
                        "verification_sha256": checksum,
                        "verification_key": report["release_prefix"] + "/verifications/" + checksum + ".json"}
                    write_json(self.store, receipt_key, receipt)
                    # Read back the durable proof before advancing coverage.
                    receipt = self.receipt(receipt_key, candidate)
                state.update(next_date=candidate["end_exclusive"],
                    verified_months=state["verified_months"] + 1,
                    verified_publications=state["verified_publications"] + candidate["records"],
                    active=None, last_verified=receipt,
                    status="complete" if candidate["end_exclusive"] == str(self.backfill.end) else "in_progress")
                state.pop("last_error", None)
                token = self.save(state, token)
                print(json.dumps({"stage": "month_verified", "month": month,
                    "release_id": receipt["release_id"], "publications": candidate["records"]}), flush=True)
        except (Exception, KeyboardInterrupt) as exc:
            # Reload: a failed/ambiguous progress write must not advance counts
            # from an uncommitted in-memory state. The immutable receipt permits
            # recovery if verification finished before the cursor was saved.
            state, token = self.state()
            error = {"at": now(), "stage": stage, "type": type(exc).__name__,
                "message": str(exc)[:500], "next_date": state["next_date"]}
            write_json(self.store, f"{self.prefix}/failures/{uuid4()}.json", error)
            state.update(status="failed", last_error=error)
            self.save(state, token)
            print(json.dumps({"publication_failed": error}), flush=True)
        return self.status()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/patent-backfill-publication.json")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--max-months", type=int)
    args = parser.parse_args()
    config = load_json(args.config)
    raw = load_json(ROOT / config["backfill_config"])
    settings = StorageSettings.load(ROOT / raw["storage_config"])
    runner = Backfill(settings.store(), settings, raw, load_json(ROOT / raw["universe"]),
                      load_json(ROOT / raw["taxonomy"]))
    publisher = Publisher(runner, load_json(ROOT / config["athena_config"]), ROOT / config["output_root"])
    if args.status:
        print(json.dumps(publisher.status()), flush=True)
        return 0
    # Share the lock with manual prepare/publish/deploy, but not raw collection.
    with (ROOT / ".patent-backfill-athena.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "busy", "reason": "publisher_already_active"}))
            return 2
        report = publisher.run(args.max_months if args.max_months is not None else config["max_months"])
    print(json.dumps(report), flush=True)
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
