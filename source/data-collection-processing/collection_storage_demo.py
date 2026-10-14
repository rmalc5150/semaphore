#!/usr/bin/env python3
"""Run a fictional partial/resume example using local files only."""

import argparse
import json

from collection_storage import AlreadyComplete, CollectionRun, LocalStore, advance_watermark, now, task_spec
from research_contract import ROOT, load_json, seal_record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, help="local directory for fictional output")
    args = parser.parse_args()
    store = LocalStore(args.output_root)
    universe = load_json(ROOT / "examples/research-contract/universe.json")
    taxonomy = load_json(ROOT / "config/sectors.v1.json")
    template = json.loads((ROOT / "examples/research-contract/records.jsonl").read_text().splitlines()[0])
    spec = task_spec("synthetic_sec_fixture", "filings", "historical",
                     "2024-06-01T00:00:00Z", "2024-07-01T00:00:00Z",
                     {"fixture": True}, "demo-1", universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, resume=True)
    except AlreadyComplete as exc:
        print(json.dumps({"status": "already_complete", "manifest": str(exc)}))
        return 0

    def record(run, number):
        return seal_record({**template, "run_id": run.run_id, "ingested_at": now(),
                            "source_record_id": f"DEMO-{number}", "payload": {"fictional": True, "page": number}})

    partial_manifest = None
    if run.cursor is None and not run.exhausted:
        run.commit_page([record(run, 1)], next_cursor="page-2")
        partial_manifest = run.finish("partial", "demonstration_interruption")
        run = CollectionRun.start(store, spec, universe, taxonomy, resume=True)
    if not run.exhausted:
        run.commit_page([record(run, 2)], exhausted=True)
    complete_manifest = run.finish("complete", expected_records=2)
    watermark = advance_watermark(store, complete_manifest, spec["window"]["start"])
    print(json.dumps({"status": "complete", "partial_manifest": partial_manifest,
                      "complete_manifest": complete_manifest, "records": run.state["record_count"],
                      "completed_until": watermark["completed_until"], "output_root": str(store.root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
