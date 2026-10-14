#!/usr/bin/env python3
"""Generate a bounded BigQuery dry-run configuration; does not execute a query."""
import argparse
from datetime import date
import json
from pathlib import Path
import unicodedata

from patent_collection import PatentMatcher, RULES_PATH
from research_contract import COLLECTION_UNIVERSE, ROOT, digest, load_json


def normalized_name(value):
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join("".join(c if c.isalnum() else " " for c in value).split())


def build(universe, rules, start, end, maximum_bytes):
    if start >= end or maximum_bytes < 1:
        raise ValueError("require start < end and a positive maximum billed byte limit")
    matcher = PatentMatcher(universe)
    names = [c["canonical_name"] for c in matcher.companies.values()]
    names += [a["alias"] for a in universe["company_aliases"]
              if a["company_id"] in matcher.companies and a["review_status"] != "rejected"]
    arrays = {"company_names": sorted({normalized_name(n) for n in names} - {""}),
        "cpc_prefixes": sorted({c for r in rules["rules"] for c in r["cpc_prefixes"]}),
        "technology_terms": sorted({t for r in rules["rules"] for t in r["terms"]})}
    parameters = [{"name": n, "parameterType": {"type": "DATE"}, "parameterValue": {"value": str(v)}}
                  for n, v in (("start_date", start), ("end_date", end))]
    parameters += [{"name": n, "parameterType": {"type": "ARRAY", "arrayType": {"type": "STRING"}},
                    "parameterValue": {"arrayValues": [{"value": x} for x in v]}} for n, v in arrays.items()]
    sql = (ROOT / "patent_discovery.sql").read_text()
    return {"configuration": {"dryRun": True, "query": {"query": sql, "useLegacySql": False,
        "parameterMode": "NAMED", "queryParameters": parameters, "maximumBytesBilled": str(maximum_bytes)}},
        "provenance": {"universe_hash": digest(universe), "classification_hash": digest(rules),
            "sql_hash": digest(sql), "universe_version": universe["universe_version"],
            "date_basis": "publication_date", "window_start": str(start), "window_end_exclusive": str(end),
            "selection": "universe_names_or_technology_candidates", "parameter_counts": {k: len(v) for k, v in arrays.items()},
            "coverage_gaps": rules["coverage_gaps"]}}


def main():
    from historical_policy import historical_start
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", type=date.fromisoformat, default=historical_start(), help="default: shared historical start")
    p.add_argument("--end", type=date.fromisoformat, required=True)
    p.add_argument("--maximum-bytes-billed", type=int, required=True)
    p.add_argument("--universe", type=Path, default=COLLECTION_UNIVERSE)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    plan = build(load_json(args.universe), load_json(RULES_PATH), args.start, args.end, args.maximum_bytes_billed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "dry_run_only": True, **plan["provenance"]}))


if __name__ == "__main__":
    main()
