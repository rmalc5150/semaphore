#!/usr/bin/env python3
"""Validate local research configuration and JSON/JSONL records without network access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_contract import ROOT, load_json, validate_record, validate_universe


def read_records(path: Path):
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if line.strip():
                    yield f"{path}:{number}", json.loads(line)
    else:
        yield str(path), load_json(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", type=Path, default=ROOT / "config/company-universe.v0.1.json")
    parser.add_argument("--taxonomy", type=Path, default=ROOT / "config/sectors.v1.json")
    parser.add_argument("--records", type=Path, action="append", default=[], help="JSON or JSONL; repeatable")
    args = parser.parse_args(argv)
    try:
        universe, taxonomy = load_json(args.universe), load_json(args.taxonomy)
        errors, warnings = validate_universe(universe, taxonomy)
        records_checked = 0
        if not errors:
            seen = set()
            for path in args.records:
                for label, record in read_records(path):
                    found = validate_record(record, universe)
                    errors.extend(f"{label}: {error}" for error in found)
                    if not found:
                        identity = record["observation_id"]
                        if identity in seen:
                            errors.append(f"{label}: duplicate observation_id {identity}")
                        seen.add(identity)
                    records_checked += 1
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "invalid", "errors": [str(exc)]}))
        return 1
    print(json.dumps({"status": "valid" if not errors else "invalid",
        "companies_checked": len(universe.get("companies", [])) if isinstance(universe, dict) else 0,
        "records_checked": records_checked, "warnings": warnings, "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
