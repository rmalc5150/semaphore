"""Shared local/S3 persistence for bounded, resumable collection tasks.

No collection, network calls, or credential loading occurs at import time.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from research_contract import canonical_json, digest, parse_instant, validate_record, validate_universe


class Conflict(RuntimeError):
    """The object exists with different bytes, or its revision has changed."""


class AlreadyComplete(RuntimeError):
    """This exact task is complete; explicitly refresh to recollect it."""


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc(value):
    return parse_instant(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def checked_key(key):
    if not isinstance(key, str) or not key or key.startswith("/") or "\\" in key:
        raise ValueError("object key must be a relative slash-separated path")
    if any(part in {"", ".", ".."} for part in key.split("/")):
        raise ValueError("object key contains an unsafe path component")
    return key


@dataclass(frozen=True)
class Stored:
    body: bytes
    token: str


class LocalStore:
    """Filesystem backend for offline work; flock + atomic replace implements CAS."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    def _path(self, key):
        path = self.root / checked_key(key)
        if self.root not in path.resolve().parents:
            raise ValueError("object path escapes output root")
        return path

    def get(self, key):
        try:
            body = self._path(key).read_bytes()
        except FileNotFoundError:
            return None
        return Stored(body, hashlib.sha256(body).hexdigest())

    def put(self, key, body, expected=None, content_type="application/json"):
        import fcntl

        path = self._path(key)
        self.root.mkdir(parents=True, exist_ok=True)
        # All writers using this backend share the same lock; readers see an
        # atomic old/new file. Intended for a local filesystem, not network FS.
        with (self.root / ".collection.lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            current = self.get(key)
            if (current.token if current else None) != expected:
                raise Conflict(f"conditional write rejected: {key}")
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                    temporary = Path(handle.name)
                    handle.write(body)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
                directory = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            finally:
                if temporary is not None and temporary.exists():
                    temporary.unlink()
        return hashlib.sha256(body).hexdigest()


class S3Store:
    """Conditional PutObject; never silently falls back to unconditional writes."""

    def __init__(self, bucket, prefix="research-data", region=None, encryption="AES256",
                 kms_key_id=None, expected_bucket_owner=None, client=None):
        if not isinstance(bucket, str) or not bucket or "/" in bucket:
            raise ValueError("s3_bucket must be a bucket name")
        self.bucket = bucket
        self.prefix = checked_key(prefix) if prefix else ""
        if encryption not in {"AES256", "aws:kms"}:
            raise ValueError("unsupported S3 encryption")
        if kms_key_id and encryption != "aws:kms":
            raise ValueError("kms_key_id requires aws:kms encryption")
        self.encryption, self.kms_key_id = encryption, kms_key_id
        self.owner = expected_bucket_owner
        if client is None:
            import boto3
            from botocore.config import Config

            client = boto3.client("s3", region_name=region,
                config=Config(signature_version="s3v4", retries={"mode": "standard", "total_max_attempts": 5}))
        self.client = client
        members = client.meta.service_model.operation_model("PutObject").input_shape.members
        if not {"IfMatch", "IfNoneMatch"}.issubset(members):
            raise RuntimeError("boto3/botocore must support conditional PutObject; install requirements.txt")

    def _args(self, key):
        key = checked_key(key)
        return {"Bucket": self.bucket, "Key": f"{self.prefix}/{key}" if self.prefix else key,
                **({"ExpectedBucketOwner": self.owner} if self.owner else {})}

    def get(self, key):
        from botocore.exceptions import ClientError

        try:
            response = self.client.get_object(**self._args(key))
        except ClientError as exc:
            # A missing bucket, forbidden object, or network failure is NOT an
            # empty checkpoint. Only a missing object is treated as absent.
            if exc.response.get("Error", {}).get("Code") == "NoSuchKey":
                return None
            raise
        stream = response["Body"]
        try:
            return Stored(stream.read(), response["ETag"])
        finally:
            stream.close()

    def put(self, key, body, expected=None, content_type="application/json"):
        from botocore.exceptions import ClientError

        args = {**self._args(key), "Body": body, "ContentType": content_type,
                "ServerSideEncryption": self.encryption,
                **({"IfNoneMatch": "*"} if expected is None else {"IfMatch": expected})}
        if self.kms_key_id:
            args["SSEKMSKeyId"] = self.kms_key_id
        try:
            return self.client.put_object(**args)["ETag"]
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") in {409, 412}:
                raise Conflict(f"conditional write rejected: {key}") from exc
            raise


def write_checked(store, key, body, expected=None, content_type="application/json"):
    """Resolve an ambiguous write acknowledgement only if stored bytes match."""
    try:
        return store.put(key, body, expected=expected, content_type=content_type)
    except Exception:
        # Covers both retries of an immutable object and a response lost after
        # the server accepted a checkpoint. Never accepts different bytes.
        current = store.get(key)
        if current is not None and current.body == body:
            return current.token
        raise


def write_json(store, key, value, expected=None):
    return write_checked(store, key, canonical_json(value) + b"\n", expected)


@dataclass(frozen=True)
class StorageSettings:
    backend: str = "local"
    local_root: str = "collection-output"
    s3_bucket: str | None = None
    s3_prefix: str = "research-data"
    region: str | None = None
    encryption: str = "AES256"
    kms_key_id: str | None = None
    expected_bucket_owner: str | None = None
    max_records_per_batch: int = 1000
    max_batch_bytes: int = 8 * 1024 * 1024

    def __post_init__(self):
        if self.backend not in {"local", "s3"}:
            raise ValueError("backend must be local or s3")
        if not isinstance(self.local_root, str) or not self.local_root:
            raise ValueError("local_root must be nonempty")
        if self.backend == "s3" and not self.s3_bucket:
            raise ValueError("s3_bucket is required for the S3 backend")
        if self.s3_prefix:
            checked_key(self.s3_prefix)
        if self.encryption not in {"AES256", "aws:kms"} or (self.kms_key_id and self.encryption != "aws:kms"):
            raise ValueError("invalid encryption settings")
        for name, maximum in (("max_records_per_batch", 100000), ("max_batch_bytes", 64 * 1024 * 1024)):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise ValueError(f"{name} must be an integer between 1 and {maximum}")

    @classmethod
    def load(cls, path=None, overrides=None, environ=None):
        values = json.loads(Path(path).read_text()) if path else {}
        env = os.environ if environ is None else environ
        for field in cls.__dataclass_fields__:
            key = "COLLECTION_" + field.upper()
            if key in env:
                values[field] = int(env[key]) if field.startswith("max_") else env[key]
        values.update({key: value for key, value in (overrides or {}).items() if value is not None})
        return cls(**values)

    def store(self, client=None):
        if self.backend == "local":
            return LocalStore(self.local_root)
        return S3Store(self.s3_bucket, self.s3_prefix, self.region, self.encryption,
                       self.kms_key_id, self.expected_bucket_owner, client)


def task_spec(source, dataset, mode, start, end, scope, collector_version, universe, taxonomy):
    """Scope contains non-secret query parameters, including company selection."""
    for value in (source, dataset):
        if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", value):
            raise ValueError("source and dataset must be lowercase identifiers")
    if mode not in {"daily", "historical"}:
        raise ValueError("mode must be daily or historical")
    if not isinstance(scope, dict) or not isinstance(collector_version, str) or not collector_version:
        raise ValueError("scope must be an object and collector_version must be nonempty")
    start, end = utc(start), utc(end)
    if parse_instant(start) >= parse_instant(end):
        raise ValueError("collection window must have start < end")
    errors, _ = validate_universe(universe, taxonomy)
    if errors:
        raise ValueError("invalid universe/taxonomy: " + "; ".join(errors))
    return {"source": source, "dataset": dataset, "mode": mode,
            "window": {"start": start, "end": end}, "scope": copy.deepcopy(scope),
            "collector_version": collector_version, "universe_version": universe["universe_version"],
            "universe_hash": digest(universe), "taxonomy_hash": digest(taxonomy)}


class CollectionRun:
    """A bounded task attempt. Checkpoints advance only after durable batches.

    Use start(..., resume=True) to take over an interrupted/partial/failed task
    after its old worker has stopped. Completed tasks require refresh=True.
    """

    @classmethod
    def start(cls, store, spec, universe, taxonomy, settings=None, resume=False, refresh=False):
        self = cls()
        self.store, self.settings = store, settings or StorageSettings()
        self.spec, self.universe = copy.deepcopy(spec), copy.deepcopy(universe)
        verified = task_spec(spec["source"], spec["dataset"], spec["mode"], spec["window"]["start"],
                             spec["window"]["end"], spec["scope"], spec["collector_version"], universe, taxonomy)
        if spec != verified:
            raise ValueError("task spec does not match the supplied configuration")
        if resume and refresh:
            raise ValueError("choose resume or refresh, not both")
        # Preserve the exact matching configuration alongside the immutable runs.
        write_json(store, f"manifests/configurations/universe/{digest(universe)}.json", universe)
        write_json(store, f"manifests/configurations/taxonomy/{digest(taxonomy)}.json", taxonomy)
        self.task_id = "task_" + digest(spec)
        self.checkpoint_key = f"checkpoints/{self.task_id}/head.json"
        stored = store.get(self.checkpoint_key)
        previous = json.loads(stored.body) if stored else None
        # Recover a crash between writing a terminal manifest and updating head.
        if previous and previous["status"] == "running":
            terminal = store.get(previous["manifest_prefix"] + "/final.json")
            if terminal:
                final = json.loads(terminal.body)
                if final["base_revision"] != previous["revision"] or final["task"] != spec:
                    raise Conflict("terminal manifest and checkpoint disagree")
                recovered = {**previous, "revision": previous["revision"] + 1,
                             "status": final["status"], "terminal_manifest": previous["manifest_prefix"] + "/final.json",
                             "terminal_history": previous["terminal_history"] + [previous["manifest_prefix"] + "/final.json"]}
                token = write_json(store, self.checkpoint_key, recovered, stored.token)
                previous, stored = recovered, Stored(canonical_json(recovered) + b"\n", token)
        if previous:
            if previous["task"] != spec:
                raise Conflict("checkpoint task identity mismatch")
            if previous["status"] == "complete" and not refresh:
                raise AlreadyComplete(previous["terminal_manifest"])
            if not resume and not refresh:
                raise Conflict("task exists; use resume after stopping its worker, or refresh")
        self.run_id = "run_" + str(uuid4())
        self.started_at = now()
        prefix = f"manifests/collection_runs/source={spec['source']}/dataset={spec['dataset']}/{self.run_id}"
        inherited = previous if previous and resume else None
        self.state = {"schema_version": "1.0", "task_id": self.task_id, "task": self.spec,
            "revision": (previous["revision"] + 1) if previous else 1,
            "run_id": self.run_id, "status": "running", "started_at": self.started_at,
            "manifest_prefix": prefix, "terminal_manifest": None,
            "terminal_history": list(previous["terminal_history"]) if previous else [],
            "resumed_from_run_id": inherited["run_id"] if inherited else None,
            "cursor": inherited["cursor"] if inherited else None,
            "exhausted": inherited["exhausted"] if inherited else False,
            "pages": copy.deepcopy(inherited["pages"]) if inherited else [],
            "record_count": inherited["record_count"] if inherited else 0,
            "duplicates_dropped": inherited["duplicates_dropped"] if inherited else 0}
        self.seen = set()
        # Validate already-committed data before letting a resume skip it.
        for page in self.state["pages"]:
            for batch in page["batches"]:
                obj = store.get(batch["key"])
                if obj is None or hashlib.sha256(obj.body).hexdigest() != batch["sha256"]:
                    raise Conflict("missing or corrupt committed batch: " + batch["key"])
                self.seen.update(json.loads(line)["observation_id"] for line in obj.body.splitlines())
        write_json(store, prefix + "/started.json", self.state)
        self.token = write_json(store, self.checkpoint_key, self.state, stored.token if stored else None)
        self.closed = False
        self.pending_final = None
        return self

    @property
    def cursor(self):
        return self.state["cursor"]

    @property
    def exhausted(self):
        return self.state["exhausted"]

    def _open(self):
        if self.closed or self.pending_final is not None:
            raise RuntimeError("run is closed or finalization is pending")
        current = self.store.get(self.checkpoint_key)
        if current is None or current.token != self.token:
            raise Conflict("checkpoint ownership changed; stop this worker")

    def commit_page(self, records, next_cursor=None, exhausted=False):
        """Commit one bounded provider page; cursor denotes its next request.

        Duplicate observation IDs within this task are dropped. Subsequent runs'
        new observations and source revisions are deliberately retained.
        """
        self._open()
        if self.exhausted:
            raise RuntimeError("source is already marked exhausted")
        if not isinstance(exhausted, bool):
            raise ValueError("exhausted must be boolean")
        if exhausted:
            if next_cursor is not None:
                raise ValueError("exhausted pages must have next_cursor=None")
        elif not isinstance(next_cursor, str) or not next_cursor or next_cursor == self.cursor:
            raise ValueError("nonterminal pages must advance to a nonempty cursor")
        if next_cursor is not None and any(next_cursor == p["cursor_after"] for p in self.state["pages"]):
            raise ValueError("pagination cursor cycle detected")
        sequence = len(self.state["pages"])
        batches, lines, size, count, duplicates = [], [], 0, 0, 0
        page_seen = set()
        day = self.started_at[:10]

        def flush():
            nonlocal lines, size
            if not lines:
                return
            body = b"".join(lines)
            checksum = hashlib.sha256(body).hexdigest()
            prefix = (f"raw/source={self.spec['source']}/dataset={self.spec['dataset']}/"
                      f"ingestion_date={day}/run_id={self.run_id}")
            key = f"{prefix}/page-{sequence:08d}-part-{len(batches):05d}-{checksum}.jsonl"
            write_checked(self.store, key, body, content_type="application/x-ndjson")
            batches.append({"key": key, "sha256": checksum, "bytes": len(body), "records": len(lines)})
            lines, size = [], 0

        for record in records:
            errors = validate_record(record, self.universe)
            if errors:
                raise ValueError("invalid collected record: " + "; ".join(errors))
            if record["run_id"] != self.run_id or record["source"] != self.spec["source"] or record["dataset"] != self.spec["dataset"]:
                raise ValueError("record must belong to this run/source/dataset")
            identity = record["observation_id"]
            if identity in self.seen or identity in page_seen:
                duplicates += 1
                continue
            line = canonical_json(record) + b"\n"
            if len(line) > self.settings.max_batch_bytes:
                raise ValueError("record exceeds max_batch_bytes; no page checkpoint was committed")
            record_day = utc(record["ingested_at"])[:10]
            if lines and (record_day != day or len(lines) >= self.settings.max_records_per_batch or size + len(line) > self.settings.max_batch_bytes):
                flush()
            day = record_day
            lines.append(line)
            size += len(line)
            count += 1
            page_seen.add(identity)
        flush()
        page = {"sequence": sequence, "run_id": self.run_id, "cursor_before": self.cursor,
                "cursor_after": next_cursor, "exhausted": exhausted, "batches": batches,
                "record_count": count, "duplicates_dropped": duplicates}
        updated = {**self.state, "revision": self.state["revision"] + 1,
            "cursor": next_cursor, "exhausted": exhausted, "pages": self.state["pages"] + [page],
            "record_count": self.state["record_count"] + count,
            "duplicates_dropped": self.state["duplicates_dropped"] + duplicates}
        # Immutable receipt precedes the CAS head. A failed CAS leaves an orphan
        # receipt/data object; only receipts reachable from head/final are committed.
        write_json(self.store, self.state["manifest_prefix"] + f"/pages/{sequence:08d}-{digest(page)}.json", page)
        token = write_json(self.store, self.checkpoint_key, updated, self.token)
        self.state, self.token = updated, token
        self.seen.update(page_seen)
        return copy.deepcopy(page)

    def finish(self, status, reason_code=None, expected_records=None):
        """Finalize an attempt. Source exhaustion must be explicitly established."""
        if self.closed:
            raise RuntimeError("run is closed")
        if status not in {"complete", "partial", "failed"}:
            raise ValueError("invalid terminal status")
        if reason_code is not None and not re.fullmatch(r"[a-z][a-z0-9_]*", reason_code):
            raise ValueError("reason_code must be a non-secret lowercase code")
        if status != "complete" and not reason_code:
            raise ValueError("partial/failed runs require a reason_code")
        if expected_records is not None and (isinstance(expected_records, bool) or not isinstance(expected_records, int) or expected_records < 0):
            raise ValueError("expected_records must be a nonnegative integer")
        if status == "complete":
            if not self.exhausted or reason_code:
                raise ValueError("complete requires source exhaustion and no error reason")
            if expected_records is not None and self.state["record_count"] != expected_records:
                raise ValueError("record count does not match expected_records")
        if self.pending_final is None:
            self._open()
            self.pending_final = {"schema_version": "1.0", "document_type": "collection_run",
                "task_id": self.task_id, "task": self.spec, "run_id": self.run_id,
                "started_at": self.started_at, "finished_at": now(), "status": status,
                "reason_code": reason_code, "expected_records": expected_records,
                "base_revision": self.state["revision"],
                "resumed_from_run_id": self.state["resumed_from_run_id"],
                "pages": self.state["pages"], "record_count": self.state["record_count"],
                "duplicates_dropped": self.state["duplicates_dropped"],
                "cursor": self.cursor, "exhausted": self.exhausted}
        elif (status, reason_code, expected_records) != tuple(self.pending_final[k] for k in ("status", "reason_code", "expected_records")):
            raise ValueError("retry finalization with the same arguments")
        key = self.state["manifest_prefix"] + "/final.json"
        write_json(self.store, key, self.pending_final)
        updated = {**self.state, "revision": self.state["revision"] + 1,
                   "status": status, "terminal_manifest": key,
                   "terminal_history": self.state["terminal_history"] + [key]}
        token = write_json(self.store, self.checkpoint_key, updated, self.token)
        self.state, self.token, self.closed = updated, token, True
        return key


def watermark_key(spec):
    stream = {k: v for k, v in spec.items() if k != "window"}
    return "checkpoints/watermarks/stream_" + digest(stream) + "/head.json"


def read_watermark(store, spec):
    """Return the last contiguous successful boundary, or None for a new stream."""
    stored = store.get(watermark_key(spec))
    if stored is None:
        return None
    value = json.loads(stored.body)
    if value["stream"] != {k: v for k, v in spec.items() if k != "window"}:
        raise Conflict("watermark stream identity mismatch")
    return value


def advance_watermark(store, manifest_key, origin):
    """Advance only across complete contiguous coverage, with an explicit origin.

    Historical/daily modes and differing scopes/configurations have separate
    watermarks. A gap must be filled before a later window can advance one.
    """
    obj = store.get(manifest_key)
    if obj is None:
        raise ValueError("manifest does not exist")
    manifest = json.loads(obj.body)
    if manifest["status"] != "complete" or not manifest["exhausted"]:
        raise ValueError("only complete source-exhausted runs can advance a watermark")
    task = manifest["task"]
    task_id = "task_" + digest(task)
    checkpoint = store.get(f"checkpoints/{task_id}/head.json")
    head = json.loads(checkpoint.body) if checkpoint else None
    if not head or manifest_key not in head["terminal_history"]:
        raise Conflict("manifest finalization is not committed in the task checkpoint")
    origin = utc(origin)
    stream = {k: v for k, v in task.items() if k != "window"}
    key = watermark_key(task)
    current = store.get(key)
    previous = json.loads(current.body) if current else None
    if previous and (previous["origin"] != origin or previous["stream"] != stream):
        raise Conflict("watermark origin or stream configuration changed")
    boundary = previous["completed_until"] if previous else origin
    start, end = task["window"]["start"], task["window"]["end"]
    if parse_instant(start) > parse_instant(boundary):
        raise ValueError("coverage gap: complete earlier windows before advancing")
    if parse_instant(end) <= parse_instant(boundary):
        if previous is None:
            raise ValueError("window ends before the requested watermark origin")
        return previous
    updated = {"schema_version": "1.0", "stream": stream, "origin": origin,
        "completed_until": end, "revision": previous["revision"] + 1 if previous else 1,
        "manifest_key": manifest_key, "previous_completed_until": boundary}
    # Audit each change immutably before switching the small mutable pointer.
    receipt = key.rsplit("/", 1)[0] + f"/history/{updated['revision']:08d}-{digest(updated)}.json"
    write_json(store, receipt, updated)
    write_json(store, key, updated, current.token if current else None)
    return updated
