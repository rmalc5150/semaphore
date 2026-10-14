"""Offline failure/recovery tests; AWS calls use botocore Stubber."""

import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import boto3
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from botocore.stub import Stubber

from collection_storage import (
    AlreadyComplete, CollectionRun, Conflict, LocalStore, S3Store, StorageSettings,
    advance_watermark, read_watermark, task_spec, write_checked,
)
from research_contract import ROOT, load_json, seal_record


class CollectionStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = LocalStore(self.temp.name)
        self.universe = load_json(ROOT / "examples/research-contract/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.template = json.loads((ROOT / "examples/research-contract/records.jsonl").read_text().splitlines()[0])
        self.spec = self.spec_for()

    def spec_for(self, start="2024-06-01T00:00:00Z", end="2024-07-01T00:00:00Z", **kwargs):
        return task_spec("synthetic_sec_fixture", "filings", kwargs.pop("mode", "historical"), start, end,
                         kwargs.pop("scope", {"fixture": True}), "test-1", self.universe, self.taxonomy, **kwargs)

    def start(self, spec=None, **kwargs):
        return CollectionRun.start(self.store, spec or self.spec, self.universe, self.taxonomy, **kwargs)

    def record(self, run, identity="one", **overrides):
        return seal_record({**copy.deepcopy(self.template), "run_id": run.run_id,
                            "source_record_id": identity, **overrides})

    def head(self, run):
        return json.loads(self.store.get(run.checkpoint_key).body)

    def complete(self, spec=None):
        run = self.start(spec)
        run.commit_page([], exhausted=True)
        return run, run.finish("complete", expected_records=0)

    def test_complete_run_writes_valid_jsonl_and_immutable_manifests(self):
        run = self.start()
        page = run.commit_page([self.record(run)], exhausted=True)
        final_key = run.finish("complete", expected_records=1)
        final = json.loads(self.store.get(final_key).body)
        self.assertEqual(final["record_count"], 1)
        body = self.store.get(page["batches"][0]["key"]).body
        self.assertEqual(len(body.splitlines()), 1)
        self.assertEqual(json.loads(body)["run_id"], run.run_id)
        self.assertEqual(self.head(run)["status"], "complete")
        with self.assertRaises(Conflict):
            write_checked(self.store, final_key, b"different")
        with self.assertRaises(AlreadyComplete):
            self.start(resume=True)

    def test_partial_run_resumes_only_after_committed_cursor(self):
        first = self.start()
        first.commit_page([self.record(first)], next_cursor="page-2")
        partial = first.finish("partial", "provider_limit")
        before = self.store.get(partial).body
        resumed = self.start(resume=True)
        self.assertEqual(resumed.cursor, "page-2")
        self.assertEqual(resumed.state["resumed_from_run_id"], first.run_id)
        resumed.commit_page([self.record(resumed, "two")], exhausted=True)
        resumed.finish("complete", expected_records=2)
        self.assertEqual(self.store.get(partial).body, before)
        self.assertEqual(resumed.state["record_count"], 2)

    def test_batch_upload_failure_does_not_advance_checkpoint(self):
        run = self.start(settings=StorageSettings(max_records_per_batch=1))
        initial = self.store.get(run.checkpoint_key)
        original = self.store.put
        writes = 0

        def fail_second(key, body, **kwargs):
            nonlocal writes
            if key.startswith("raw/"):
                writes += 1
                if writes == 2:
                    raise OSError("simulated write failure")
            return original(key, body, **kwargs)

        with patch.object(self.store, "put", side_effect=fail_second):
            with self.assertRaises(OSError):
                run.commit_page([self.record(run, "one"), self.record(run, "two")], next_cursor="next")
        self.assertEqual(self.store.get(run.checkpoint_key), initial)
        self.assertEqual(run.state["record_count"], 0)
        run.commit_page([self.record(run, "one"), self.record(run, "two")], exhausted=True)
        run.finish("complete", expected_records=2)

    def test_checkpoint_failure_keeps_uploaded_data_uncommitted(self):
        run = self.start()
        original = self.store.put

        def fail_checkpoint(key, body, **kwargs):
            if key == run.checkpoint_key:
                raise OSError("checkpoint unavailable")
            return original(key, body, **kwargs)

        with patch.object(self.store, "put", side_effect=fail_checkpoint):
            with self.assertRaises(OSError):
                run.commit_page([self.record(run)], exhausted=True)
        self.assertEqual(self.head(run)["pages"], [])
        self.assertFalse(run.exhausted)
        run.commit_page([self.record(run)], exhausted=True)
        run.finish("complete")

    def test_lost_write_acknowledgement_is_reconciled(self):
        run = self.start()
        original = self.store.put

        def accepted_then_lost(key, body, **kwargs):
            original(key, body, **kwargs)
            raise OSError("response lost")

        with patch.object(self.store, "put", side_effect=accepted_then_lost):
            run.commit_page([self.record(run)], exhausted=True)
            run.finish("complete")
        self.assertEqual(self.head(run)["status"], "complete")

    def test_resume_fences_previous_worker(self):
        first = self.start()
        second = self.start(resume=True)
        with self.assertRaises(Conflict):
            first.commit_page([self.record(first)], exhausted=True)
        self.assertEqual(self.head(second)["run_id"], second.run_id)

    def test_crash_after_final_manifest_is_recovered(self):
        run = self.start()
        run.commit_page([], exhausted=True)
        original = self.store.put

        def fail_checkpoint(key, body, **kwargs):
            if key == run.checkpoint_key:
                raise OSError("head update failed")
            return original(key, body, **kwargs)

        with patch.object(self.store, "put", side_effect=fail_checkpoint):
            with self.assertRaises(OSError):
                run.finish("complete", expected_records=0)
        self.assertEqual(self.head(run)["status"], "running")
        with self.assertRaises(AlreadyComplete):
            self.start(resume=True)
        self.assertEqual(self.head(run)["status"], "complete")

    def test_finalization_retry_preserves_identical_manifest(self):
        run = self.start()
        run.commit_page([], exhausted=True)
        original = self.store.put

        def fail_checkpoint(key, body, **kwargs):
            if key == run.checkpoint_key:
                raise OSError("head update failed")
            return original(key, body, **kwargs)

        with patch.object(self.store, "put", side_effect=fail_checkpoint):
            with self.assertRaises(OSError):
                run.finish("complete")
        before = self.store.get(run.state["manifest_prefix"] + "/final.json").body
        key = run.finish("complete")
        self.assertEqual(self.store.get(key).body, before)

    def test_complete_requires_exhaustion_and_expected_count(self):
        run = self.start()
        with self.assertRaises(ValueError):
            run.finish("complete")
        run.commit_page([], exhausted=True)
        with self.assertRaises(ValueError):
            run.finish("complete", expected_records=10)
        with self.assertRaises(ValueError):
            run.finish("partial")
        run.finish("partial", "count_mismatch")

    def test_empty_success_and_failure_are_distinct(self):
        run = self.start()
        key = run.finish("failed", "source_unavailable")
        self.assertFalse(json.loads(self.store.get(key).body)["exhausted"])
        resumed = self.start(resume=True)
        resumed.commit_page([], exhausted=True)
        key = resumed.finish("complete", expected_records=0)
        self.assertEqual(json.loads(self.store.get(key).body)["record_count"], 0)

    def test_duplicate_observations_are_dropped_within_and_across_pages(self):
        run = self.start()
        record = self.record(run)
        run.commit_page([record, record], next_cursor="two")
        run.commit_page([record], exhausted=True)
        self.assertEqual(run.state["record_count"], 1)
        self.assertEqual(run.state["duplicates_dropped"], 2)

    def test_refresh_creates_new_observations_without_overwriting_prior_run(self):
        first, key = self.complete()
        before = self.store.get(key).body
        fresh = self.start(refresh=True)
        self.assertNotEqual(fresh.run_id, first.run_id)
        self.assertEqual(fresh.state["pages"], [])
        self.assertIn(key, self.head(fresh)["terminal_history"])
        watermark = advance_watermark(self.store, key, self.spec["window"]["start"])
        self.assertEqual(watermark["completed_until"], self.spec["window"]["end"])
        fresh.commit_page([self.record(fresh)], exhausted=True)
        fresh.finish("complete")
        self.assertEqual(self.store.get(key).body, before)

    def test_uncommitted_terminal_manifest_cannot_advance_watermark(self):
        run = self.start()
        run.commit_page([], exhausted=True)
        original = self.store.put

        def fail_checkpoint(key, body, **kwargs):
            if key == run.checkpoint_key:
                raise OSError("head update failed")
            return original(key, body, **kwargs)

        with patch.object(self.store, "put", side_effect=fail_checkpoint):
            with self.assertRaises(OSError):
                run.finish("complete")
        key = run.state["manifest_prefix"] + "/final.json"
        with self.assertRaises(Conflict):
            advance_watermark(self.store, key, self.spec["window"]["start"])

    def test_batch_record_limit_and_ingestion_date_partition(self):
        run = self.start(settings=StorageSettings(max_records_per_batch=1))
        page = run.commit_page([self.record(run, "one"), self.record(run, "two", ingested_at="2026-09-18T01:00:00Z")], exhausted=True)
        self.assertEqual(len(page["batches"]), 2)
        self.assertIn("ingestion_date=2026-09-18", page["batches"][1]["key"])

    def test_batch_byte_limit_splits_and_rejects_oversize(self):
        run = self.start(settings=StorageSettings(max_batch_bytes=2200))
        page = run.commit_page([self.record(run, "one"), self.record(run, "two")], exhausted=True)
        self.assertEqual(len(page["batches"]), 2)
        fresh = self.start(refresh=True, settings=StorageSettings(max_batch_bytes=10))
        with self.assertRaises(ValueError):
            fresh.commit_page([self.record(fresh)], exhausted=True)
        self.assertEqual(self.head(fresh)["pages"], [])

    def test_invalid_or_wrong_run_record_is_rejected(self):
        run = self.start()
        bad = self.record(run)
        bad["payload"]["tampered"] = True
        with self.assertRaises(ValueError):
            run.commit_page([bad], exhausted=True)
        with self.assertRaises(ValueError):
            run.commit_page([self.template], exhausted=True)
        self.assertEqual(self.head(run)["pages"], [])

    def test_cursor_must_advance_and_cannot_cycle(self):
        run = self.start()
        run.commit_page([], next_cursor="a")
        with self.assertRaises(ValueError):
            run.commit_page([], next_cursor="a")
        run.commit_page([], next_cursor="b")
        with self.assertRaises(ValueError):
            run.commit_page([], next_cursor="a")
        with self.assertRaises(ValueError):
            run.commit_page([], next_cursor="c", exhausted=True)

    def test_corrupt_committed_data_blocks_resume(self):
        run = self.start()
        page = run.commit_page([self.record(run)], next_cursor="two")
        key = page["batches"][0]["key"]
        original = self.store.get(key)
        self.store.put(key, b"corrupt", expected=original.token)
        with self.assertRaises(Conflict):
            self.start(resume=True)

    def test_watermark_requires_complete_and_contiguous_coverage(self):
        run = self.start()
        partial = run.finish("partial", "provider_limit")
        with self.assertRaises(ValueError):
            advance_watermark(self.store, partial, self.spec["window"]["start"])
        run = self.start(resume=True)
        run.commit_page([], exhausted=True)
        key = run.finish("complete")
        first = advance_watermark(self.store, key, self.spec["window"]["start"])
        self.assertEqual(first["completed_until"], "2024-07-01T00:00:00Z")
        gap_spec = self.spec_for("2024-08-01T00:00:00Z", "2024-09-01T00:00:00Z")
        _, gap_key = self.complete(gap_spec)
        with self.assertRaises(ValueError):
            advance_watermark(self.store, gap_key, self.spec["window"]["start"])
        bridge = self.spec_for("2024-07-01T00:00:00Z", "2024-08-01T00:00:00Z")
        _, bridge_key = self.complete(bridge)
        advance_watermark(self.store, bridge_key, self.spec["window"]["start"])
        last = advance_watermark(self.store, gap_key, self.spec["window"]["start"])
        self.assertEqual(last["completed_until"], "2024-09-01T00:00:00Z")
        self.assertEqual(advance_watermark(self.store, key, self.spec["window"]["start"]), last)

    def test_initial_watermark_cannot_skip_configured_origin(self):
        _, key = self.complete()
        with self.assertRaises(ValueError):
            advance_watermark(self.store, key, "2024-05-01T00:00:00Z")

    def test_read_watermark_returns_only_the_successful_stream_boundary(self):
        self.assertIsNone(read_watermark(self.store, self.spec))
        _, key = self.complete()
        expected = advance_watermark(self.store, key, self.spec["window"]["start"])
        next_window = self.spec_for("2024-07-01T00:00:00Z", "2024-08-01T00:00:00Z")
        self.assertEqual(read_watermark(self.store, next_window), expected)
        self.assertIsNone(read_watermark(self.store, self.spec_for(mode="daily")))

    def test_modes_scopes_and_config_changes_have_different_tasks(self):
        first = self.start()
        second = self.start(self.spec_for(mode="daily"))
        third = self.start(self.spec_for(scope={"company_ids": []}))
        self.assertEqual(len({r.task_id for r in [first, second, third]}), 3)
        changed = copy.deepcopy(self.spec)
        changed["universe_hash"] = "bad"
        with self.assertRaises(ValueError):
            self.start(changed)

    def test_settings_precedence_validation_and_no_implicit_cloud(self):
        path = Path(self.temp.name) / "config.json"
        path.write_text('{"local_root":"from-file"}')
        settings = StorageSettings.load(path, {"local_root": "override"}, {"COLLECTION_LOCAL_ROOT": "env"})
        self.assertEqual(settings.local_root, "override")
        self.assertEqual(settings.backend, "local")
        with self.assertRaises(ValueError):
            StorageSettings(backend="s3")
        with self.assertRaises(ValueError):
            StorageSettings(max_records_per_batch=0)

    def test_path_traversal_is_rejected(self):
        for key in ("../outside", "/absolute", "x/../y", "x\\y", "x//y"):
            with self.assertRaises(ValueError):
                self.store.put(key, b"bad")


class S3StorageTests(unittest.TestCase):
    def setUp(self):
        self.client = boto3.client("s3", region_name="us-east-1", aws_access_key_id="test-only",
                                   aws_secret_access_key="test-only")
        self.stub = Stubber(self.client)
        self.stub.activate()
        self.addCleanup(self.stub.deactivate)
        self.store = S3Store("example-research-bucket", "research", client=self.client)

    def test_create_and_compare_and_swap_use_required_preconditions(self):
        base = {"Bucket": "example-research-bucket", "Key": "research/object.json", "Body": b"{}",
                "ContentType": "application/json", "ServerSideEncryption": "AES256"}
        self.stub.add_response("put_object", {"ETag": '"one"'}, {**base, "IfNoneMatch": "*"})
        self.stub.add_response("put_object", {"ETag": '"two"'}, {**base, "IfMatch": '"one"'})
        self.assertEqual(self.store.put("object.json", b"{}"), '"one"')
        self.assertEqual(self.store.put("object.json", b"{}", expected='"one"'), '"two"')
        self.stub.assert_no_pending_responses()

    def test_stale_write_becomes_conflict(self):
        self.stub.add_client_error("put_object", "PreconditionFailed", http_status_code=412)
        with self.assertRaises(Conflict):
            self.store.put("object.json", b"{}", expected='"old"')

    def test_missing_key_is_not_confused_with_permissions_or_missing_bucket(self):
        args = {"Bucket": "example-research-bucket", "Key": "research/object.json"}
        self.stub.add_client_error("get_object", "NoSuchKey", http_status_code=404, expected_params=args)
        self.stub.add_client_error("get_object", "AccessDenied", http_status_code=403, expected_params=args)
        self.stub.add_client_error("get_object", "NoSuchBucket", http_status_code=404, expected_params=args)
        self.assertIsNone(self.store.get("object.json"))
        with self.assertRaises(ClientError):
            self.store.get("object.json")
        with self.assertRaises(ClientError):
            self.store.get("object.json")

    def test_idempotent_s3_retry_checks_existing_bytes(self):
        self.stub.add_client_error("put_object", "PreconditionFailed", http_status_code=412)
        self.stub.add_response("get_object", {"ETag": '"one"', "Body": StreamingBody(io.BytesIO(b"{}"), 2)})
        self.assertEqual(write_checked(self.store, "object.json", b"{}"), '"one"')

    def test_kms_and_expected_bucket_owner(self):
        store = S3Store("example-research-bucket", "", encryption="aws:kms", kms_key_id="test-key",
                        expected_bucket_owner="123456789012", client=self.client)
        args = {"Bucket": "example-research-bucket", "Key": "object.json", "Body": b"{}",
                "ContentType": "application/json", "ServerSideEncryption": "aws:kms", "SSEKMSKeyId": "test-key",
                "ExpectedBucketOwner": "123456789012", "IfNoneMatch": "*"}
        self.stub.add_response("put_object", {"ETag": '"one"'}, args)
        store.put("object.json", b"{}")
        self.stub.assert_no_pending_responses()


if __name__ == "__main__":
    unittest.main()
