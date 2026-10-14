#!/usr/bin/env python3
"""Read back selected news runs, retaining partial/failed coverage distinctions."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from collection_storage import StorageSettings
from regulatory_collection import require
from research_contract import ROOT, canonical_json, digest, load_json, validate_record


def audit(store, report):
    results, verified = [], set()
    for result in report["results"]:
        key = result["manifest"]
        manifest = json.loads(store.get(key).body)
        task = manifest["task"]
        head = json.loads(store.get("checkpoints/task_" + digest(task) + "/head.json").body)
        require(key in head["terminal_history"] and head["task"] == task and manifest["task_id"] == "task_" + digest(task), "news_manifest_not_committed")
        require(manifest["status"] == result["status"], "news_report_status_mismatch")
        universe = json.loads(store.get("manifests/configurations/universe/" + task["universe_hash"] + ".json").body)
        require(digest(universe) == task["universe_hash"], "news_universe_hash_mismatch")
        ids, records, languages, metadata = set(), 0, Counter(), []
        def evidence(ref):
            if ref["key"] not in verified:
                obj = store.get(ref["key"])
                require(obj is not None and hashlib.sha256(obj.body).hexdigest() == ref["sha256"], "news_evidence_hash_mismatch")
                verified.add(ref["key"])
            data = json.loads(store.get(ref["key"]).body)
            if "articles" in data or "data" in data:
                metadata.append({"status": data.get("status"), "page": data.get("page"),
                    "pageSize": data.get("pageSize"), "meta": data.get("meta"),
                    "returned": len(data.get("articles", data.get("data", [])))})
        for page in manifest["pages"]:
            count = 0
            for batch in page["batches"]:
                body = store.get(batch["key"]).body
                require(len(body) == batch["bytes"] and hashlib.sha256(body).hexdigest() == batch["sha256"], "news_raw_hash_mismatch")
                rows = [json.loads(line) for line in body.splitlines()]
                require(len(rows) == batch["records"], "news_batch_count_mismatch")
                for record in rows:
                    require(not validate_record(record, universe), "invalid_news_record")
                    require(record["observation_id"] not in ids, "duplicate_news_observation")
                    require(record["run_id"] == page["run_id"] and record["source"] == task["source"] and record["dataset"] == task["dataset"], "news_record_scope_mismatch")
                    ids.add(record["observation_id"])
                    languages[record["payload"]["data"].get("language") or "unknown"] += 1
                    for ref in record["payload"]["source_evidence"]:
                        if ref["key"] not in verified: evidence(ref)
                count += len(rows)
            require(count == page["record_count"], "news_page_count_mismatch")
            records += count
            prefix = f"manifests/collection_runs/source={task['source']}/dataset=news_articles/{page['run_id']}"
            response = json.loads(store.get(prefix + f"/responses/{page['sequence']:08d}.json").body)
            for ref in response["evidence"]:
                if ref["key"] not in verified: evidence(ref)
        failure = store.get(key.rsplit("/", 1)[0] + "/failure.json")
        if failure:
            for ref in json.loads(failure.body)["evidence"]:
                if ref["key"] not in verified: evidence(ref)
        require(records == manifest["record_count"], "news_manifest_count_mismatch")
        results.append({**result, "records_verified": records, "languages": dict(languages), "response_metadata": metadata})
    return {"evidence_audit": "passed", "records_verified": sum(r["records_verified"] for r in results),
        "source_documents_verified": len(verified), "athena_published": False,
        "coverage_note": "Integrity audit, not proof of historical entitlement or complete news coverage.", "results": results}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    settings = StorageSettings.load(ROOT / "config/collection-storage.s3.json")
    result = audit(settings.store(), load_json(args.report))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(result) + b"\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
