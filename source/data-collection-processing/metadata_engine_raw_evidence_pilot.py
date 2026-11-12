"""One-record SEC raw-evidence gate; it intentionally publishes no corpus."""
from __future__ import annotations

import hashlib
import json

import boto3

from metadata_engine.contracts import load_contract
from metadata_engine.labelling import label_observation


BUCKET = "data-collection-059416028963-us-east-1-an"
KEY = "research-data/raw/source=sec_edgar/dataset=filings/ingestion_date=2026-09-17/run_id=run_017c2a87-e157-4cef-be58-8342cb6d2418/page-00000000-part-00000-d4d52b4583e0ab816de889d2789e4587eecaf656115c6bf8fea7e3f2f7f79b63.jsonl"


def main():
    s3 = boto3.client("s3", region_name="us-east-1")
    response = s3.get_object(Bucket=BUCKET, Key=KEY)
    try:
        raw = response["Body"].read()
    finally:
        response["Body"].close()
    original = json.loads(raw.splitlines()[0])
    contract = load_contract("metadata_engine/contracts/sec_edgar.v1.json")
    candidate = {**original, "raw_s3_uri": "s3://" + BUCKET + "/" + KEY,
                 "raw_sha256": hashlib.sha256(raw).hexdigest(),
                 "raw_completeness_status": "complete",
                 "raw_artifacts": [{"artifact_kind": "provider_record", "s3_uri": "s3://" + BUCKET + "/" + KEY,
                                    "sha256": hashlib.sha256(raw).hexdigest(), "origin": "first_party_source"}]}
    try:
        label_observation(candidate, contract, labelled_at="2026-10-30T15:00:00+00:00")
    except ValueError as error:
        print(json.dumps({"pilot": "sec_edgar_one_record", "source_record_id": original["source_record_id"],
                          "disposition": "rejected_not_published", "reason": str(error),
                          "missing_requirement": "primary_document", "raw_object": candidate["raw_s3_uri"]}, indent=2))
        return
    raise RuntimeError("pilot unexpectedly accepted a source record without its primary document")


if __name__ == "__main__":
    main()
