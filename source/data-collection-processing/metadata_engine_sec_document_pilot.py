"""One committed SEC accession: retrieve original bytes and test its contract.

Outputs are isolated pilot artifacts, never analytical publication. A retrieval
failure is a durable failed pilot, not empty success.
"""
from __future__ import annotations

import hashlib
import json
import socket
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError

import boto3

from metadata_engine.contracts import load_contract
from metadata_engine.labelling import label_observation
from metadata_engine.sec_documents import archive_submission, retrieve_submission

BUCKET = "data-collection-059416028963-us-east-1-an"
KEY = "research-data/raw/source=sec_edgar/dataset=filings/ingestion_date=2026-09-17/run_id=run_017c2a87-e157-4cef-be58-8342cb6d2418/page-00000000-part-00000-d4d52b4583e0ab816de889d2789e4587eecaf656115c6bf8fea7e3f2f7f79b63.jsonl"
MANIFEST = "manifests/collection_runs/source=sec_edgar/dataset=filings/run_017c2a87-e157-4cef-be58-8342cb6d2418/final.json"
HEAD = "research-data/checkpoints/task_4fb1f3d42e3fb76a3199afb0b74178ce16b785c32aba341f8ce01dbb2d32f4a9/head.json"
ACCESSION = "0000950170-24-067660"


def read(s3, key, limit=2 * 1024 * 1024):
    response = s3.get_object(Bucket=BUCKET, Key=key)
    try:
        body = response["Body"].read(limit + 1)
    finally:
        response["Body"].close()
    if len(body) > limit:
        raise ValueError("pilot_input_size_limit")
    return body


def write(s3, key, body):
    s3.put_object(Bucket=BUCKET, Key=key, Body=body, ServerSideEncryption="AES256", ContentType="application/json", IfNoneMatch="*")
    if read(s3, key) != body:
        raise ValueError("pilot_output_readback_mismatch")
    return "s3://" + BUCKET + "/" + key


def committed_input(s3):
    head = json.loads(read(s3, HEAD))
    if MANIFEST not in head.get("terminal_history", []):
        raise ValueError("pilot_manifest_not_committed")
    manifest_body = read(s3, "research-data/" + MANIFEST)
    manifest = json.loads(manifest_body)
    if manifest.get("status") != "complete":
        raise ValueError("pilot_manifest_not_complete")
    matches = [batch for page in manifest["pages"] for batch in page["batches"] if "research-data/" + batch["key"] == KEY]
    if len(matches) != 1:
        raise ValueError("pilot_batch_not_in_manifest")
    raw = read(s3, KEY)
    if len(raw) != matches[0]["bytes"] or hashlib.sha256(raw).hexdigest() != matches[0]["sha256"]:
        raise ValueError("pilot_batch_checksum_mismatch")
    if len(raw.splitlines()) != matches[0]["records"]:
        raise ValueError("pilot_batch_count_mismatch")
    original = json.loads(raw.splitlines()[0])
    if original["source_record_id"] != ACCESSION:
        raise ValueError("pilot_record_identity_changed")
    return original, raw, hashlib.sha256(manifest_body).hexdigest()


def main():
    s3 = boto3.client("s3", region_name="us-east-1")
    run_id = str(uuid.uuid4())
    prefix = "research-data/constellation-backfill/metadata-engine/pilots/sec-document/" + run_id
    report = {"pilot": "sec_edgar_one_record_with_document", "run_id": run_id, "source_record_id": ACCESSION,
              "started_at": datetime.now(timezone.utc).isoformat(), "input_records_selected": 1,
              "production_published": False, "database_writes": 0}
    try:
        original, raw, manifest_hash = committed_input(s3)
        report.update(input_manifest="s3://" + BUCKET + "/research-data/" + MANIFEST, input_manifest_sha256=manifest_hash)
        contract = load_contract(Path(__file__).parent / "metadata_engine/contracts/sec_edgar.v1.json")
        body, receipt = retrieve_submission(original)
        artifact = archive_submission(s3, BUCKET, body, receipt)
        receipt_uri = write(s3, prefix + "/retrieval.json", json.dumps(artifact, sort_keys=True, indent=2).encode())
        artifact["retrieval_receipt_uri"] = receipt_uri
        candidate = {**original, "raw_s3_uri": "s3://" + BUCKET + "/" + KEY,
                     "raw_sha256": hashlib.sha256(raw).hexdigest(), "raw_completeness_status": "complete",
                     "raw_artifacts": [{"artifact_kind": "provider_record", "s3_uri": "s3://" + BUCKET + "/" + KEY,
                                        "sha256": hashlib.sha256(raw).hexdigest(), "origin": "first_party_source",
                                        "representation": "existing collected-record envelope from SEC index"}, artifact]}
        labelled = label_observation(candidate, contract)
        labelled_uri = write(s3, prefix + "/labelled.json", json.dumps(labelled, sort_keys=True, indent=2).encode())
        report.update(disposition="accepted_pilot_only", raw_document=artifact, labelled_pilot_uri=labelled_uri,
                      record_id=labelled["record_id"], source_observation_id=original["observation_id"],
                      historical_availability=labelled["availability_basis"])
    except (ValueError, URLError, TimeoutError, socket.timeout) as error:
        report.update(disposition="rejected_not_published", reason=str(error)[:300], error_type=type(error).__name__)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report_uri = write(s3, prefix + "/report.json", json.dumps(report, sort_keys=True, indent=2).encode())
    print(json.dumps({**report, "report_uri": report_uri}, indent=2))
    if report["disposition"] != "accepted_pilot_only":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
