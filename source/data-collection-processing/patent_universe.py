#!/usr/bin/env python3
"""Promote audited patent registry entities and receipt relationships into universe 0.3."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pyarrow.parquet as pq

from patent_entity_review import checked_body
from research_contract import ROOT, canonical_json, digest, load_json, validate_universe
from sec_athena_pilot import require

ENTITY_ROOT = ROOT / "patent-entity-build/19b5e77645eec2c15f7d3f4b5639c4d42c351cbd8c18fb382992998d0122b8b0"
ATHENA_ROOT = ROOT / "patent-athena-build/0aebe0d989788fc9a9913b4a3f5edde818aca1a75f6b5c7b6c99c0c03a65b3cb"
BUSINESS_ROOT = ROOT / "reports/patent-universe-business-evidence-2026-09-23"


def evidence(source, reference, note):
    return {"source": source, "reference": reference, "note": note}


def stable_id(registry, table, key, prefix):
    if key not in registry[table]:
        registry[table][key] = prefix + "_" + str(uuid4())
    return registry[table][key]


def promote(parent, registry, entities, listing_rows, business, observed):
    universe, registry = deepcopy(parent), deepcopy(registry)
    require(parent["universe_version"] == "0.2.0", "Explicit 0.2 parent required")
    universe.update(universe_version="0.3.0", created_at=observed)
    companies = {r["company_id"]: r for r in universe["companies"]}
    lei_owners = {}
    for identifier in universe["external_identifiers"]:
        if identifier["system"] == "lei" and identifier["review_status"] == "verified":
            require(identifier["value"] not in lei_owners or lei_owners[identifier["value"]] == identifier["entity_id"], "Conflicting verified LEIs")
            lei_owners[identifier["value"]] = identifier["entity_id"]
    mapping, additions = {}, []
    policies = {
        "988400QX6P286XA6ZS85": ("energy_storage", ["batteries"], "verified", "lg_energy"),
        "41BNNE1AFPNAZELZ6K07": ("semiconductors", ["semiconductor_equipment"], "verified", "applied_materials"),
        "9884004ARY4RODDUCT12": ("semiconductors", [], "pending", "samsung_display"),
        "988400P37K91W0SABO95": ("semiconductors", [], "pending", "lg_display"),
    }
    for entity in entities:
        if not entity["selected_lei"]:
            continue
        lei = entity["selected_lei"]
        selected = next(c for c in entity["candidates"] if c["lei"] == lei)
        require(entity["status"] == "registry_name_supported" and selected["eligible"], "Unverified registry entity")
        key = "lei:" + lei
        cid = lei_owners.get(lei)
        if cid:
            require(companies[cid]["review_status"] == "verified" and companies[cid]["entity_type"] == "legal_entity", "Existing LEI owner is not a verified legal entity")
            require(registry["company_keys"].get(key, cid) == cid, "ID registry conflicts with verified owner")
            registry["company_keys"][key] = cid
        else:
            require(lei in policies, "Unreviewed entity promotion")
            cid = stable_id(registry, "company_keys", key, "cmp")
            require(cid not in companies, "Registry maps new LEI to an unrelated existing company")
            sector, subsectors, status, source_key = policies[lei]
            source = business[source_key]
            ev = evidence("gleif", selected["registry_url"], "Current legal identity corroborated; response sha256:" + entity["evidence"]["sha256"])
            sector_ev = evidence("official_business_review", source["url"], source["note"] + "; source sha256:" + source["sha256"])
            company = {"company_id": cid, "canonical_name": selected["legal_name"], "entity_type": "legal_entity",
                "ownership_status": "unknown", "domicile_country": selected["legal_address"]["country"],
                "collection_enabled": status == "verified", "sectors": [{"sector_id": sector, "subsector_ids": subsectors,
                    "classification_basis": "reviewed_current_official_business_description" if status == "verified" else "display_manufacturing_scope_needs_review",
                    "valid_from": None, "valid_to": None, "observed_at": observed, "review_status": status, "evidence": [sector_ev]}],
                "observed_at": observed, "review_status": "verified", "evidence": [ev]}
            universe["companies"].append(company); companies[cid] = company
            xid = stable_id(registry, "identifier_keys", cid + "|lei|" + lei, "xid")
            universe["external_identifiers"].append({"identifier_id": xid, "entity_id": cid, "system": "lei", "value": lei,
                "valid_from": None, "valid_to": None, "observed_at": observed, "review_status": "verified", "evidence": [ev]})
            additions.append(cid)
        mapping[key] = cid
        # Preserve source spelling and registry-provided English name. Unknown
        # historical boundaries remain null; these are current-name evidence.
        names = {entity["reported_name"]: "source_name"}
        names.update({m["name"]: "legal_name" for m in selected["matched_names"]})
        existing = {(r["company_id"], r["alias"], r["alias_type"]) for r in universe["company_aliases"]}
        for name, kind in sorted(names.items()):
            if (cid, name, kind) in existing:
                continue
            aid = stable_id(registry, "alias_keys", cid + "|" + name.casefold() + "|" + kind, "als")
            universe["company_aliases"].append({"alias_id": aid, "company_id": cid, "alias": name, "language": "en",
                "alias_type": kind, "valid_from": None, "valid_to": None, "observed_at": observed, "review_status": "verified",
                "evidence": [evidence("gleif_patent_entity_review", selected["registry_url"],
                    "Current reviewed registry/source name; historical validity not established; sha256:" + entity["evidence"]["sha256"])]})
    listings = {r["listing_id"]: r for r in universe["listings"]}
    changed, retired = [], set()
    for review in listing_rows:
        if review["review_status"] != "supported":
            continue
        listing = listings[review["listing_id"]]
        require(listing["company_id"] == review["original_company_id"] and listing["ticker"] == review["ticker"] and
            listing["exchange_mic"] == review["exchange_mic"], "Listing review does not match parent")
        require(review["relationship_type"] == "depositary_receipt_on_underlying_issuer", "Unsupported listing relationship")
        old = listing["company_id"]
        cid = mapping[review["registry_entity_id"]]
        ev = evidence("exchange_listing_notice", review["source_url"], "Receipt issuer: " + review["depositary_issuer_name"] +
            "; research company_id identifies the underlying issuer, not the depositary; source sha256:" + review["source_sha256"])
        def day(v): return v.isoformat() if v else None
        listing.update(company_id=cid, company_role="underlying_issuer", depositary_issuer_name=review["depositary_issuer_name"],
            security_type=review["reviewed_security_type"], valid_from=day(review["listed_from"]),
            valid_to=day(review["valid_to_exclusive"]), trading_from=day(review["trading_from"]), observed_at=observed,
            review_status="verified", evidence=listing["evidence"] + [ev])
        changed.append({"listing_id": listing["listing_id"], "old_company_id": old, "underlying_company_id": cid,
            "relationship_type": review["relationship_type"], "source_url": review["source_url"]})
        retired.add(old)
    for cid in retired:
        require(not any(l["company_id"] == cid for l in universe["listings"]), "Placeholder still has an unresolved listing")
        company = companies[cid]
        require(company["review_status"] == "pending" and not any(i["entity_id"] == cid and i["review_status"] == "verified" for i in universe["external_identifiers"]), "Cannot retire a verified legal entity")
        company.update(collection_enabled=False, review_status="rejected", observed_at=observed)
        company["evidence"].append(evidence("patent_listing_reconciliation", "universe:0.3.0",
            "Rejected as a standalone legal-company identity: receipt-derived placeholder. ID retained for old observations; listing now points to supported underlying issuer. This is not a legal-entity merger."))
    return universe, registry, {"registry_entity_company_ids": mapping, "new_company_ids": additions,
        "listing_changes": changed, "retired_placeholder_ids": sorted(retired),
        "sector_pending_company_ids": [c for c in additions if not companies[c]["collection_enabled"]]}


def build(parent_path, registry_path, output_path, report_path):
    parent, registry = load_json(parent_path), load_json(registry_path)
    er, ar = load_json(ENTITY_ROOT / "review.json"), load_json(ATHENA_ROOT / "release.json")
    verify = load_json(ATHENA_ROOT / "athena-verification.json")
    require(verify["status"] == "verified" and verify["release_id"] == ar["release_id"], "Patent Athena release not verified")
    require(er["universe_hash"] == ar["universe_hash"] == digest(parent), "Parent universe hash mismatch")
    require(ar["config"]["entity_review_id"] == er["release_id"], "Mixed patent reviews")
    entities = [json.loads(line) for line in checked_body(ENTITY_ROOT / "entities.jsonl", er["files"]["entities.jsonl"]).splitlines()]
    meta = ar["files"]["patent_listing_reviews"]
    checked_body(ATHENA_ROOT / meta["path"], meta)
    listing_rows = pq.read_table(ATHENA_ROOT / meta["path"]).to_pylist()
    business = {}
    notes = {"lg_energy": "Official company describes automotive, mobility and energy-storage batteries",
        "samsung_display": "Official company describes OLED displays; chip-sector membership needs explicit scope review",
        "lg_display": "Official company describes OLED/LCD display panels; chip-sector membership needs explicit scope review"}
    for info in load_json(BUSINESS_ROOT / "manifest.json"):
        raw = checked_body(BUSINESS_ROOT / info["file"], info)
        require((b"battery" if info["name"] == "lg_energy" else b"oled") in raw.lower(), "Business evidence does not support review")
        business[info["name"]] = {**info, "note": notes[info["name"]]}
    applied = next(r for r in listing_rows if r["ticker"] == "AMAT01")
    business["applied_materials"] = {"url": applied["source_url"], "sha256": applied["source_sha256"],
        "note": "Exchange notice describes equipment and solutions for semiconductor manufacturing"}
    # A stable observation timestamp keeps repeat builds byte-identical.
    observed = max(x["retrieved_at"] for x in business.values() if "retrieved_at" in x)
    universe, new_registry, delta = promote(parent, registry, entities, listing_rows, business, observed)
    errors, warnings = validate_universe(universe, load_json(ROOT / "config/sectors.v1.json"))
    require(not errors, "Invalid promoted universe: " + "; ".join(errors[:10]))
    for table, key in (("companies", "company_id"), ("listings", "listing_id"), ("company_aliases", "alias_id"), ("external_identifiers", "identifier_id")):
        require({r[key] for r in parent[table]} <= {r[key] for r in universe[table]}, "Existing identity lost: " + table)
    report = {"version": "patent-universe-promotion-1.0", "generated_at": observed, "universe_version": "0.3.0",
        "parent_universe_hash": digest(parent), "universe_hash": digest(universe), "entity_review_id": er["release_id"],
        "patent_athena_release_id": ar["release_id"], **delta, "validation_warnings": warnings,
        "company_status_counts": dict(Counter(c["review_status"] for c in universe["companies"])),
        "companies": len(universe["companies"]), "listings": len(universe["listings"]),
        "aliases": len(universe["company_aliases"]), "external_identifiers": len(universe["external_identifiers"]),
        "business_evidence": business, "historical_identity_status": "not_established", "ownership_status": "not_established"}
    for path, value in ((output_path, universe), (report_path, report)):
        if Path(path).exists():
            require(load_json(Path(path)) == value, "Existing versioned output differs; select a new version")
    # Mutate the stable ID registry only after every candidate output validates.
    Path(registry_path).write_text(json.dumps(new_registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    Path(output_path).write_text(json.dumps(universe, ensure_ascii=False, indent=2) + "\n")
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    coverage = deepcopy(load_json(ROOT / "reports/company-universe-v0.2-coverage.json"))
    coverage.update(universe_version="0.3.0", generated_at=observed, universe_company_entities=len(universe["companies"]),
        universe_listings=len(universe["listings"]), universe_aliases=len(universe["company_aliases"]),
        universe_external_identifiers=len(universe["external_identifiers"]), verified_company_entities=report["company_status_counts"].get("verified",0),
        pending_company_entities=report["company_status_counts"].get("pending",0), rejected_company_entities=report["company_status_counts"].get("rejected",0),
        promoted_sector_memberships=sum(s["review_status"] == "verified" for c in universe["companies"] for s in c["sectors"]),
        universe_validation_warnings=warnings, patent_promotion=report,
        eodhd_coverage_observed_at="2026-09-22T18:04:24.081358Z", coverage_note="EODHD counts describe the original 9438-profile release, not current collection progress; patent registry additions are a separate reviewed cohort.")
    (ROOT / "reports/company-universe-v0.3-coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k:v for k,v in report.items() if k not in {"validation_warnings", "business_evidence"}}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--parent", type=Path, default=ROOT / "config/company-universe.v0.2.json")
    p.add_argument("--registry", type=Path, default=ROOT / "config/company-id-registry.v1.json")
    p.add_argument("--output", type=Path, default=ROOT / "config/company-universe.v0.3.json")
    p.add_argument("--report", type=Path, default=ROOT / "reports/patent-universe-promotion-2026-09-23.json")
    p.add_argument("--prepare-athena", action="store_true")
    a = p.parse_args()
    build(a.parent, a.registry, a.output, a.report)
    if a.prepare_athena:
        from collection_storage import StorageSettings
        from company_universe_athena import prepare
        prepare(StorageSettings.load(ROOT / "config/collection-storage.s3.json"), load_json(ROOT / "config/company-universe-athena.json"),
            a.output, ROOT / "config/sectors.v1.json", ROOT / "reports/company-universe-v0.3-coverage.json",
            ROOT / "reports/private-company-candidates-2026-09-22.json", a.registry, a.report, ROOT / "company-universe-build",
            extra_artifacts=[BUSINESS_ROOT / "manifest.json"] + sorted(BUSINESS_ROOT.glob("*.html")))


if __name__ == "__main__":
    main()
