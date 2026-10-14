#!/usr/bin/env python3
"""Validate committed patent evidence and generate a local company/sector review."""
import argparse
from collections import Counter
import json
from pathlib import Path

from collection_storage import StorageSettings
from regulatory_athena import read_inputs
from research_contract import ROOT, digest
from sec_athena_pilot import get_bytes, require


def review(store, manifests):
    entries, universe, inputs = read_inputs(store, manifests,
        allowed={"google_patents_bigquery", "uspto_odp"}, dataset="patent_records")
    countries, sources, sectors, categories, company_sectors = (Counter() for _ in range(5))
    companies = {c["company_id"]: c for c in universe["companies"]}
    rows, windows = [], []
    for item in inputs:
        manifest = json.loads(get_bytes(store, item["key"]))
        task = manifest["task"]
        checksum = task["scope"]["classification_hash"]
        rules = json.loads(get_bytes(store, f"manifests/configurations/patent_classification/{checksum}.json"))
        require(digest(rules) == checksum, "Classification checksum mismatch")
        windows.append({"source": task["source"], "mode": task["mode"], "window": task["window"],
            "scope": task["scope"], "records": manifest["record_count"], "manifest": item["key"]})
    for identity, entry in sorted(entries.items()):
        r = entry["record"]
        p, data = r["payload"], r["payload"]["data"]
        sources[r["source"]] += 1
        countries[data["country_code"]] += 1
        sectors.update(set(x["sector_id"] for x in p["technology_classifications"]))
        categories.update(set(x["category"] for x in p["technology_classifications"]))
        company_sectors.update(set(p["candidate_sector_ids"]))
        rows.append({"observation_id": identity, "record_id": r["record_id"], "source": r["source"],
            "publication_number": data.get("publication_number"), "application_number": data.get("application_number"),
            "family_id": data.get("family_id"), "country_code": data["country_code"], "title": data.get("title"),
            "assignees": data["assignees"], "applicants": data["applicants"],
            "candidate_companies": [{"company_id": cid, "name": companies[cid]["canonical_name"],
                "identity_review_status": companies[cid]["review_status"]} for cid in p["candidate_company_ids"]],
            "candidate_company_sectors": p["candidate_sector_ids"],
            "technology_classifications": p["technology_classifications"],
            "publication_date": data.get("publication_date"), "filing_date": data.get("filing_date"),
            "available_at": r["available_at"], "source_url": r["source_url"], "manifests": sorted(entry["manifests"])})
    return {"status": "evidence_verified_review_pending", "universe_version": universe["universe_version"],
        "inputs": inputs, "windows": windows, "observations": len(rows),
        "unique_source_records": len({r["record_id"] for r in rows}), "by_source": dict(sources),
        "by_publication_authority": dict(countries), "technology_sector_observations": dict(sectors),
        "technology_category_observations": dict(categories), "candidate_company_sector_observations": dict(company_sectors),
        "observations_with_company_candidates": sum(bool(r["candidate_companies"]) for r in rows),
        "missing_publication_date": sum(not r["publication_date"] for r in rows),
        "point_in_time_eligible": sum(r["available_at"] is not None for r in rows),
        "athena_publication_status": "not_published", "rows": rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", action="append", required=True)
    p.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = review(StorageSettings.load(args.storage_config).store(), args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"rows", "windows", "inputs"}}))


if __name__ == "__main__":
    main()
