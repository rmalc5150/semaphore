"""Local validation and identity helpers for the research data contract.

No network requests, credential loading, collection, or file writes occur here.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker


ROOT = Path(__file__).resolve().parent
COLLECTION_UNIVERSE = ROOT / "config/company-universe.v0.2.json"
SCHEMA_PATH = ROOT / "schemas" / "research-data.schema.json"
ENTITY_TABLES = {
    "companies": "company_id", "listings": "listing_id",
    "products": "product_id", "people": "person_id",
}
IDENTITY_TABLES = {
    **ENTITY_TABLES, "company_aliases": "alias_id",
    "external_identifiers": "identifier_id", "relationships": "relationship_id",
}
RELATION_TYPES = {
    "subsidiary_of": ("cmp", "cmp"), "business_unit_of": ("cmp", "cmp"),
    "owns": ("cmp", "prd"), "develops": ("cmp", "prd"),
    "manufactures": ("cmp", "prd"), "licenses_in": ("cmp", "prd"),
    "licenses_out": ("cmp", "prd"), "employed_by": ("per", "cmp"),
    "board_member_of": ("per", "cmp"),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(value: Any) -> bytes:
    """Contract v1 canonicalization, not a claim of RFC 8785 compliance."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def record_id(source: str, dataset: str, source_record_id: str) -> str:
    return "rec_" + digest(["record-v1", source, dataset, source_record_id])


def seal_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a new envelope with deterministic record/payload/observation hashes.

    Identical envelopes (including run ID and ingestion time) produce identical
    observation IDs. Any other envelope change produces a new observation.
    """
    result = dict(record)
    result["record_id"] = record_id(result["source"], result["dataset"], result["source_record_id"])
    result["payload_hash"] = "sha256:" + digest(result["payload"])
    result.pop("observation_id", None)
    result["observation_id"] = "obs_" + digest(result)
    return result


@lru_cache(maxsize=8)
def _validator(kind: str):
    schema = load_json(SCHEMA_PATH)
    selected = {"$schema": schema["$schema"], "$ref": "#/definitions/" + kind,
                "definitions": schema["definitions"]}
    return Draft7Validator(selected, format_checker=FormatChecker())


def schema_errors(document: Any, kind: str) -> list[str]:
    return [f"{'.'.join(map(str, error.absolute_path)) or '$'}: {error.message}"
            for error in sorted(_validator(kind).iter_errors(document), key=lambda e: str(list(e.path)))]


def parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a UTC offset")
    return parsed


def temporal_errors(value: Any, path: str = "$") -> list[str]:
    """Check dates even if optional jsonschema format dependencies are absent."""
    errors = []
    if isinstance(value, list):
        for i, item in enumerate(value):
            errors.extend(temporal_errors(item, f"{path}[{i}]"))
    elif isinstance(value, dict):
        if {"value", "precision", "source_timezone"}.issubset(value):
            stamp, precision = value["value"], value["precision"]
            try:
                if precision == "day":
                    date.fromisoformat(stamp)
                    if len(stamp) != 10:
                        raise ValueError("day precision requires YYYY-MM-DD")
                else:
                    parse_instant(stamp)
                    fraction = re.search(r"\.(\d+)", stamp)
                    digits = len(fraction.group(1)) if fraction else 0
                    bounds = {"second": (0, 0), "millisecond": (1, 3), "microsecond": (4, 6)}
                    lo, hi = bounds[precision]
                    if not lo <= digits <= hi:
                        raise ValueError("precision does not match fractional seconds")
            except (ValueError, KeyError) as exc:
                errors.append(f"{path}: invalid time value: {exc}")
        for key, item in value.items():
            # A provider's raw payload is not governed by our timestamp schema.
            if key == "payload":
                continue
            try:
                if key in {"created_at", "observed_at", "ingested_at"}:
                    parse_instant(item)
                elif key in {"valid_from", "valid_to"} and item is not None:
                    date.fromisoformat(item)
            except ValueError as exc:
                errors.append(f"{path}.{key}: {exc}")
            errors.extend(temporal_errors(item, f"{path}.{key}"))
        if value.get("valid_from") and value.get("valid_to"):
            if value["valid_from"] >= value["valid_to"]:
                errors.append(f"{path}: valid_to must be later than valid_from (exclusive end)")
    return errors


def overlaps(a: dict, b: dict) -> bool:
    """Conservative collision check: unknown boundaries may overlap."""
    return ((a.get("valid_from") or "0001-01-01") < (b.get("valid_to") or "9999-12-31")
            and (b.get("valid_from") or "0001-01-01") < (a.get("valid_to") or "9999-12-31"))


def validate_taxonomy(taxonomy: dict) -> list[str]:
    errors = schema_errors(taxonomy, "taxonomy")
    if errors:
        return errors
    sector_ids, subsector_ids = set(), set()
    for sector in taxonomy["sectors"]:
        sid = sector["sector_id"]
        if sid in sector_ids:
            errors.append(f"duplicate sector_id: {sid}")
        sector_ids.add(sid)
        for sub in sector["subsectors"]:
            if sub["subsector_id"] in subsector_ids:
                errors.append(f"duplicate subsector_id: {sub['subsector_id']}")
            subsector_ids.add(sub["subsector_id"])
    storage = next((s for s in taxonomy["sectors"] if s["sector_id"] == "energy_storage"), None)
    required = {"batteries", "supercapacitors", "thermal_storage", "mechanical_storage", "hydrogen_storage"}
    if storage is None or not required.issubset({s["subsector_id"] for s in storage["subsectors"]}):
        errors.append("energy_storage must include all five agreed storage subsectors")
    return errors


def validate_universe(universe: dict, taxonomy: dict) -> tuple[list[str], list[str]]:
    errors = schema_errors(universe, "universe") + validate_taxonomy(taxonomy)
    warnings = []
    if errors:
        return errors, warnings
    errors.extend(temporal_errors(universe))
    if universe["taxonomy_version"] != taxonomy["taxonomy_version"]:
        errors.append("taxonomy_version does not match the supplied taxonomy")
    ids, entities = set(), {}
    for table, key in IDENTITY_TABLES.items():
        for row in universe[table]:
            identity = row[key]
            if identity in ids:
                errors.append(f"duplicate ID: {identity}")
            ids.add(identity)
            if table in ENTITY_TABLES:
                entities[identity] = row
    companies = {c["company_id"] for c in universe["companies"]}
    sectors = {s["sector_id"]: {sub["subsector_id"] for sub in s["subsectors"]} for s in taxonomy["sectors"]}
    for company in universe["companies"]:
        memberships = company["sectors"]
        for i, membership in enumerate(memberships):
            if not set(membership["subsector_ids"]).issubset(sectors[membership["sector_id"]]):
                errors.append(f"{company['company_id']}: subsector does not belong to sector")
            for previous in memberships[:i]:
                if previous["sector_id"] == membership["sector_id"] and overlaps(previous, membership):
                    errors.append(f"{company['company_id']}: overlapping duplicate sector memberships")
    for table in ("company_aliases", "listings"):
        for row in universe[table]:
            if row["company_id"] not in companies:
                errors.append(f"{table}: unknown company_id {row['company_id']}")
    for listing in universe["listings"]:
        if listing.get("company_role") == "underlying_issuer":
            if listing["security_type"] not in {"adr", "gdr", "depositary_receipt", "canadian_depositary_receipt"} or not listing.get("depositary_issuer_name"):
                errors.append(f"{listing['listing_id']}: underlying issuer requires a receipt and a distinct depositary issuer")
        if listing.get("trading_from"):
            if (listing["valid_from"] and listing["trading_from"] < listing["valid_from"]) or (listing["valid_to"] and listing["trading_from"] >= listing["valid_to"]):
                errors.append(f"{listing['listing_id']}: trading start outside listing validity")
    for row in universe["external_identifiers"]:
        if row["entity_id"] not in entities:
            errors.append(f"unknown entity_id: {row['entity_id']}")
    for row in universe["relationships"]:
        subject, object_ = row["subject_id"], row["object_id"]
        if subject not in entities or object_ not in entities:
            errors.append(f"{row['relationship_id']}: unknown relationship endpoint")
        if subject == object_:
            errors.append(f"{row['relationship_id']}: self relationship is not allowed")
        expected = RELATION_TYPES[row["relationship_type"]]
        if (subject.split('_')[0], object_.split('_')[0]) != expected:
            errors.append(f"{row['relationship_id']}: invalid endpoint types for {row['relationship_type']}")
    # These conflicts could assign a source record to the wrong company.
    for table, key_fn, owner_key in (
        ("external_identifiers", lambda r: (r["system"], r["value"]), "entity_id"),
        ("listings", lambda r: (r["exchange_mic"], r["ticker"]), "listing_id"),
    ):
        seen = {}
        for row in universe[table]:
            if row["review_status"] != "verified":
                continue
            key = key_fn(row)
            for other in seen.get(key, []):
                if row[owner_key] != other[owner_key] and overlaps(row, other):
                    errors.append(f"{table}: conflicting verified identifier {key}")
            seen.setdefault(key, []).append(row)
    aliases = {}
    for row in universe["company_aliases"]:
        key = " ".join(row["alias"].casefold().split())
        for other in aliases.get(key, []):
            if row["company_id"] != other["company_id"] and overlaps(row, other):
                warnings.append(f"ambiguous alias {row['alias']!r}; do not auto-match")
        aliases.setdefault(key, []).append(row)
    pending = sum(c["review_status"] != "verified" or c["entity_type"] == "unresolved_organization"
                  for c in universe["companies"])
    if pending:
        warnings.append(f"{pending} company entries are provisional; suitable for discovery, not verified historical entity matching")
    return errors, warnings


def validate_record(record: dict, universe: dict) -> list[str]:
    errors = schema_errors(record, "record")
    if errors:
        return errors
    errors.extend(temporal_errors(record))
    if record["universe_version"] != universe["universe_version"]:
        errors.append("record universe_version does not match the supplied universe")
    matched = 0
    for table, key in ENTITY_TABLES.items():
        valid = {row[key] for row in universe[table]}
        field = key + "s"
        matched += len(record[field])
        for identity in record[field]:
            if identity not in valid:
                errors.append(f"{field}: unknown entity {identity}")
    if record["entity_match_status"] == "unresolved" and matched:
        errors.append("unresolved records cannot contain resolved entity IDs; use partial")
    if record["entity_match_status"] != "unresolved" and not matched:
        errors.append("matched/partial records require at least one entity ID")
    for listing in universe["listings"]:
        if listing["listing_id"] in record["listing_ids"] and listing["company_id"] not in record["company_ids"]:
            errors.append("a referenced listing's company must also be in company_ids")
    if record["available_at"] is None:
        if record["availability_basis"] != "unknown" or record["availability_evidence"]:
            errors.append("unknown availability requires basis=unknown and no availability evidence")
    elif record["availability_basis"] == "unknown" or not record["availability_evidence"]:
        errors.append("known availability requires a stated basis and supporting evidence")
    try:
        expected = seal_record(record)
    except (ValueError, TypeError) as exc:
        errors.append(f"record is not canonical JSON: {exc}")
        return errors
    for field in ("record_id", "payload_hash", "observation_id"):
        if record[field] != expected[field]:
            errors.append(f"{field} does not match the contract identity algorithm")
    return errors
