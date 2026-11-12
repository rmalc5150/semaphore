"""Versioned, compact JSON source-contract loader."""
from __future__ import annotations

import json
from pathlib import Path


REQUIRED = {"source_key", "contract_version", "adapter", "adapter_version", "record_kind", "license_policy_id", "raw_requirements"}


def load_contract(path: str | Path) -> dict:
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = REQUIRED - contract.keys()
    if missing:
        raise ValueError("contract missing: " + ", ".join(sorted(missing)))
    requirements = contract["raw_requirements"]
    if not isinstance(requirements, dict) or not requirements.get("required_artifact_kinds"):
        raise ValueError("contract raw_requirements must name required_artifact_kinds")
    if requirements.get("minimum_completeness") not in {"complete"}:
        raise ValueError("only complete raw-data contracts may be published")
    return contract
