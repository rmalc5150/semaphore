#!/usr/bin/env python3
"""Publish versioned patent reviews and assignment evidence to bounded Athena tables."""
import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import html
import json
from pathlib import Path
import re

import pyarrow as pa
import pyarrow.parquet as pq

from collection_storage import StorageSettings, checked_key, write_checked
from patent_entity_review import checked_body, name_key
from patent_query_plan import normalized_name
from regulatory_athena import read_inputs
from research_contract import ROOT, canonical_json, digest, load_json
import sec_athena_pilot as release

VERSION = "patent-athena-1.0"


def strings(*names):
    return [(n, "string") for n in names]


SCHEMAS = {
    "patent_publications": strings("observation_id", "record_id", "source", "publication_number", "application_number",
        "publication_authority", "title", "source_url", "source_payload_hash", "source_evidence_json", "available_at",
        "current_ownership_status") + [("publication_date", "date"), ("reported_company_names", "array<string>"),
        ("supported_sector_ids", "array<string>"), ("supported_company_ids", "array<string>"),
        ("registry_entity_ids", "array<string>"), ("review_reasons", "array<string>"),
        ("has_supported_name_link", "boolean"), ("point_in_time_eligible", "boolean")],
    "patent_sector_reviews": strings("observation_id", "publication_number", "sector_id", "category", "review_status", "basis",
        "evidence_json") + [("cpc_codes", "array<string>")],
    "patent_party_links": strings("observation_id", "publication_number", "reported_name", "party_role", "original_status",
        "review_status", "company_id", "registry_entity_id", "link_basis", "historical_identity_status", "current_ownership_status",
        "evidence_json") + [("candidate_company_ids", "array<string>")],
    "patent_entity_reviews": strings("reported_name", "review_status", "registry_entity_id", "selected_lei", "legal_name",
        "jurisdiction", "registry_url", "evidence_json", "candidates_json", "historical_identity_status", "current_ownership_status")
        + [("publication_count", "bigint")],
    "patent_company_reconciliation": strings("registry_entity_id", "legal_name", "company_id", "review_status", "basis")
        + [("candidate_company_ids", "array<string>"), ("supported_underlying_listing_ids", "array<string>")],
    "patent_listing_reviews": strings("listing_id", "original_company_id", "exchange_mic", "ticker", "original_security_type",
        "reviewed_security_type", "registry_entity_id", "relationship_type", "depositary_issuer_name", "review_status", "basis",
        "source_url", "source_sha256", "source_observed_at", "original_listing_json") + [("listed_from", "date"),
        ("trading_from", "date"), ("valid_to_exclusive", "date"), ("source_date", "date"), ("point_in_time_eligible", "boolean")],
    "patent_assignment_histories": strings("observation_id", "application_number", "source_url", "source_evidence_json",
        "comparison_status", "current_ownership_status", "chain_completeness", "assignment_history_json")
        + [("assignment_event_count", "bigint"), ("point_in_time_eligible", "boolean")],
    "patent_assignment_events": strings("observation_id", "application_number", "reel_frame", "event_kind", "conveyance",
        "document_url", "assignees_json", "assignors_json", "current_ownership_status") + [("event_index", "bigint"),
        ("recorded_date", "date"), ("received_date", "date"), ("recipient_names", "array<string>"), ("is_latest_recorded_assignment", "boolean")],
    "patent_coverage": strings("patent_review_id", "entity_review_id", "assignment_review_id", "universe_hash", "coverage_note",
        "unresolved_listing_ids_json", "source_manifests_json") + [("publications", "bigint"), ("supported_technology_publications", "bigint"),
        ("supported_name_publications", "bigint"), ("assignment_applications", "bigint"), ("publication_start", "date"),
        ("publication_end", "date"), ("current_ownership_verified_records", "bigint"), ("point_in_time_eligible_records", "bigint")],
}


def as_date(value):
    return date.fromisoformat(value) if value else None


def read_review(store, root, prefix, identity):
    root = Path(root)
    body = (root / "review.json").read_bytes()
    release.require(body == release.get_bytes(store, prefix + "/" + identity + "/review.json"), "Published review differs from local review")
    report = json.loads(body)
    release.require(report["release_id"] == identity, "Review identity mismatch")
    for name, meta in report["files"].items():
        checked_key(name)
        checked_body(root / name, meta)
        raw = release.get_bytes(store, prefix + "/" + identity + "/" + name)
        release.require(len(raw) == meta["bytes"] and hashlib.sha256(raw).hexdigest() == meta["sha256"], "Published review artifact checksum mismatch")
    return report


def read_jsonl(path):
    with Path(path).open() as handle:
        for line in handle:
            yield json.loads(line)


def verify_patent_inputs(store, report):
    """Anchor an already audited immutable review to committed raw manifests.

    The review publisher previously verified every source response and record.
    Here those exact published artifacts are checked again, and their manifest
    and configuration anchors must still be committed and unchanged.
    """
    universe = None
    for info in report["inputs"]:
        body = release.get_bytes(store, info["key"])
        release.require(hashlib.sha256(body).hexdigest() == info["sha256"], "Patent manifest checksum mismatch")
        manifest = json.loads(body)
        task = manifest["task"]
        release.require(manifest["status"] == "complete" and manifest["exhausted"] and
            manifest["record_count"] == manifest["expected_records"] == info["records"], "Patent input not complete")
        release.require(task["dataset"] == "patent_records" and task["universe_hash"] == report["universe_hash"], "Patent input scope mismatch")
        task_id = "task_" + digest(task)
        head = json.loads(release.get_bytes(store, "checkpoints/" + task_id + "/head.json"))
        release.require(manifest["task_id"] == task_id and head["task"] == task and info["key"] in head["terminal_history"], "Uncommitted patent input")
        universe = json.loads(release.get_bytes(store, "manifests/configurations/universe/" + task["universe_hash"] + ".json"))
        release.require(digest(universe) == task["universe_hash"], "Universe checksum mismatch")
    release.require(universe is not None, "Missing patent inputs")
    return universe


def listing_reviews(universe, entities, policy, evidence_root):
    release.require(policy["universe_hash"] == digest(universe), "Listing review universe mismatch")
    registry = {r["registry_entity_id"]: r for r in entities if r["selected_lei"]}
    evidence_root = Path(evidence_root)
    sources = {r["name"]: r for r in load_json(evidence_root / "manifest.json")}
    decisions = {r["listing_id"]: r for r in policy["decisions"]}
    release.require(len(decisions) == len(policy["decisions"]), "Duplicate listing decision")
    listings = {l["listing_id"]: l for l in universe["listings"]}
    candidate_companies = set()
    for c in universe["companies"]:
        if any(name_key(c["canonical_name"]) == name_key(r["reported_name"]) for r in registry.values()):
            candidate_companies.add(c["company_id"])
    for lid, decision in decisions.items():
        release.require(lid in listings and decision["registry_entity_id"] in registry, "Unknown reviewed listing or registry entity")
        listing = listings[lid]
        release.require((listing["exchange_mic"], listing["ticker"]) == (decision["exchange_mic"], decision["ticker"]), "Listing identity mismatch")
        candidate_companies.add(listing["company_id"])
    rows = []
    for lid, listing in sorted(listings.items()):
        if listing["company_id"] not in candidate_companies:
            continue
        decision = decisions.get(lid)
        row = {"listing_id": lid, "original_company_id": listing["company_id"], "exchange_mic": listing["exchange_mic"],
            "ticker": listing["ticker"], "original_security_type": listing["security_type"], "reviewed_security_type": None,
            "registry_entity_id": None, "relationship_type": None, "depositary_issuer_name": None,
            "review_status": "pending", "basis": "Need exchange or issuer evidence; a company name/LEI does not verify a listing",
            "source_url": None, "source_sha256": None, "source_observed_at": None, "source_date": None,
            "listed_from": None, "trading_from": None, "valid_to_exclusive": None,
            "original_listing_json": release.json_text(listing), "point_in_time_eligible": False}
        if decision:
            source = sources[decision["source_name"]]
            text = checked_body(evidence_root / checked_key(source["file"]), source).decode()
            text = re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", text)))
            release.require(all(s in text for s in decision["required_text"]), "Listing source no longer supports reviewed facts")
            for k in ("registry_entity_id", "relationship_type", "depositary_issuer_name"):
                row[k] = decision[k]
            for k in ("listed_from", "trading_from", "valid_to_exclusive", "source_date"):
                row[k] = as_date(decision[k])
            release.require(row["listed_from"] <= row["trading_from"] and
                (row["valid_to_exclusive"] is None or row["valid_to_exclusive"] > row["trading_from"]), "Invalid listing date bounds")
            row.update(reviewed_security_type=decision["security_type"], review_status="supported",
                basis="Reviewed exchange notice; underlying issuer is distinct from depositary issuer",
                source_url=source["url"], source_sha256=source["sha256"], source_observed_at=source["retrieved_at"])
        rows.append(row)
    return rows


def reconcile(universe, entities, listings):
    verified = defaultdict(set)
    companies = {c["company_id"]: c for c in universe["companies"]}
    for identifier in universe["external_identifiers"]:
        company = companies.get(identifier["entity_id"])
        if identifier["system"] == "lei" and identifier["review_status"] == "verified" and company and (
                company["entity_type"] == "legal_entity" and company["review_status"] == "verified"):
            verified[identifier["value"]].add(company["company_id"])
    rows = []
    for entity in entities:
        if not entity["selected_lei"]:
            continue
        selected = next(c for c in entity["candidates"] if c["lei"] == entity["selected_lei"])
        matches = sorted(verified[entity["selected_lei"]])
        linked_listings = [l for l in listings if l["registry_entity_id"] == entity["registry_entity_id"]]
        candidates = {c["company_id"] for c in companies.values() if name_key(c["canonical_name"]) == name_key(entity["reported_name"])}
        candidates.update(l["original_company_id"] for l in linked_listings)
        rows.append({"registry_entity_id": entity["registry_entity_id"], "legal_name": selected["legal_name"],
            "company_id": matches[0] if len(matches) == 1 else None,
            "review_status": "verified_identifier_link" if len(matches) == 1 else "identifier_conflict" if matches else "new_legal_entity_or_listing_reconciliation_needed",
            "basis": "Exact verified LEI; listing-underlying relationships never merge legal company IDs",
            "candidate_company_ids": sorted(candidates), "supported_underlying_listing_ids": sorted(l["listing_id"] for l in linked_listings)})
    return rows


def publication_rows(decisions, entities, reconciled):
    """Yield independent publication, sector and party rows without title inference."""
    by_name = {normalized_name(r["reported_name"]): r for r in entities}
    company_for_entity = {r["registry_entity_id"]: r["company_id"] for r in reconciled if r["company_id"]}
    seen = set()
    for d in decisions:
        oid = d["observation_id"]
        release.require(oid not in seen, "Duplicate patent observation")
        seen.add(oid)
        release.require(not d["point_in_time_eligible"] and not d["current_owner_company_ids"], "Unexpected unreviewed title/model eligibility claim")
        parties = []
        for p in d["reported_parties"]:
            entity = by_name.get(normalized_name(p["reported_name"]))
            eid = entity["registry_entity_id"] if entity else None
            status = entity["status"] if entity else p["status"]
            cid = p["company_id"]
            if eid:
                cid = company_for_entity.get(eid)
            # Unresolved registry evidence must not leave a previous supported
            # name link looking verified under a new ambiguous status.
            if status != "registry_name_supported":
                cid = None
            parties.append({"observation_id": oid, "publication_number": d["publication_number"],
                "reported_name": p["reported_name"], "party_role": p["role"], "original_status": p["status"],
                "review_status": status, "company_id": cid, "registry_entity_id": eid,
                "link_basis": "reviewed_gleif_name" if entity else p["reason"],
                "historical_identity_status": "not_established", "current_ownership_status": "not_established",
                "candidate_company_ids": p["candidate_company_ids"],
                "evidence_json": release.json_text({"original": p, "registry_review_name": entity["reported_name"] if entity else None})})
        for p in parties:
            yield "patent_party_links", p
        for status, reviews in (("supported", d["supported_technology"]), ("pending", d["pending_technology"])):
            for r in reviews:
                yield "patent_sector_reviews", {"observation_id": oid, "publication_number": d["publication_number"],
                    "sector_id": r["sector_id"], "category": r["category"], "review_status": status,
                    "basis": r.get("basis") or r.get("reason"), "evidence_json": release.json_text(r), "cpc_codes": r.get("cpc_codes", r.get("cpc_hits", []))}
        reasons = [r for r in d["review_reasons"] if r in {"technology_document_review_needed", "no_reported_assignee_or_applicant"}]
        reasons += sorted({p["review_status"] for p in parties if p["review_status"] != "registry_name_supported"})
        yield "patent_publications", {"observation_id": oid, "record_id": d["record_id"], "source": d["source"],
            "publication_number": d["publication_number"], "application_number": d["application_number"],
            "publication_authority": d["publication_number"].split("-", 1)[0], "title": d["title"],
            "source_url": d["source_url"], "source_payload_hash": d["source_payload_hash"],
            "source_evidence_json": release.json_text(d["source_evidence"]), "available_at": None,
            "current_ownership_status": "not_established", "publication_date": as_date(d["publication_date"]),
            "reported_company_names": sorted({p["reported_name"] for p in parties}),
            "supported_sector_ids": d["research_sector_ids"], "supported_company_ids": sorted({p["company_id"] for p in parties if p["company_id"]}),
            "registry_entity_ids": sorted({p["registry_entity_id"] for p in parties if p["registry_entity_id"]}),
            "review_reasons": sorted(set(reasons)), "has_supported_name_link": any(p["review_status"] == "registry_name_supported" for p in parties),
            "point_in_time_eligible": False}


def assignment_rows(entries, comparisons):
    observed_apps = set()
    for entry in entries.values():
        r = entry["record"]
        app = r["source_record_id"]
        release.require(app not in observed_apps, "Multiple assignment observations need explicit snapshot selection")
        observed_apps.add(app)
        history = r["payload"]["data"]["assignment_history"]
        comparison = comparisons.get(r["observation_id"])
        yield "patent_assignment_histories", {"observation_id": r["observation_id"], "application_number": app,
            "source_url": r["source_url"], "source_evidence_json": release.json_text(r["payload"]["source_evidence"]),
            "comparison_status": comparison["comparison_status"] if comparison else "outside_registry_comparison_cohort",
            "current_ownership_status": "not_established", "chain_completeness": history["chain_completeness"],
            "assignment_history_json": release.json_text(history), "assignment_event_count": len(history["events"]), "point_in_time_eligible": False}
        for i, e in enumerate(history["events"]):
            yield "patent_assignment_events", {"observation_id": r["observation_id"], "application_number": app,
                "event_index": i, "reel_frame": e["reel_frame"], "event_kind": e["event_kind"], "conveyance": e["conveyance"],
                "document_url": e["document_url"], "assignees_json": release.json_text(e["assignees"]),
                "assignors_json": release.json_text(e["assignors"]), "current_ownership_status": "not_established",
                "recorded_date": as_date(e["recorded_date"]), "received_date": as_date(e["received_date"]),
                "recipient_names": sorted({a["assigneeNameText"] for a in e["assignees"] if a.get("assigneeNameText")}),
                "is_latest_recorded_assignment": e in history["latest_recorded_assignment_events"]}


def validation(tables, db):
    queries = {"table_counts": " UNION ALL ".join(f"SELECT '{n}' AS table_name, count(*) FROM {db}.{n}" for n in sorted(tables)) + " ORDER BY 1",
        "quality": f"SELECT count(*), count(DISTINCT observation_id), count(DISTINCT publication_number), count_if(has_supported_name_link), count_if(point_in_time_eligible), count_if(current_ownership_status <> 'not_established'), count(available_at) FROM {db}.patent_publications",
        "sectors": f"SELECT sector_id, count(DISTINCT observation_id) FROM {db}.patent_sector_reviews WHERE review_status='supported' GROUP BY sector_id ORDER BY sector_id",
        "listing_status": f"SELECT review_status, count(*) FROM {db}.patent_listing_reviews GROUP BY review_status ORDER BY review_status",
        "assignment_status": f"SELECT comparison_status, count(*) FROM {db}.patent_assignment_histories GROUP BY comparison_status ORDER BY comparison_status",
        "date_window": f"SELECT min(publication_date), max(publication_date), count_if(publication_authority='CN') FROM {db}.patent_publications",
        "referential_integrity": f"SELECT (SELECT count(*) FROM {db}.patent_party_links l LEFT JOIN {db}.patent_publications p ON l.observation_id=p.observation_id WHERE p.observation_id IS NULL), (SELECT count(*) FROM {db}.patent_sector_reviews l LEFT JOIN {db}.patent_publications p ON l.observation_id=p.observation_id WHERE p.observation_id IS NULL), (SELECT count(*) FROM {db}.patent_assignment_events e LEFT JOIN {db}.patent_assignment_histories h ON e.observation_id=h.observation_id WHERE h.observation_id IS NULL)",
        "preview": f"SELECT publication_number, publication_date, title, supported_sector_ids, has_supported_name_link, current_ownership_status FROM {db}.patent_publications ORDER BY publication_number LIMIT 10"}
    pubs = tables["patent_publications"]
    sectors = defaultdict(set)
    for r in tables["patent_sector_reviews"]:
        if r["review_status"] == "supported":
            sectors[r["sector_id"]].add(r["observation_id"])
    dates = [r["publication_date"] for r in pubs if r["publication_date"]]
    expected = {"table_counts": [[n, str(len(r))] for n, r in sorted(tables.items())],
        "quality": [[str(len(pubs)), str(len({r['observation_id'] for r in pubs})), str(len({r['publication_number'] for r in pubs})), str(sum(r['has_supported_name_link'] for r in pubs)), "0", "0", "0"]],
        "sectors": [[s, str(len(ids))] for s, ids in sorted(sectors.items())],
        "date_window": [[str(min(dates)) if dates else None, str(max(dates)) if dates else None, str(sum(r['publication_authority']=='CN' for r in pubs))]],
        "referential_integrity": [["0", "0", "0"]]}
    for key, table, column in (("listing_status", "patent_listing_reviews", "review_status"), ("assignment_status", "patent_assignment_histories", "comparison_status")):
        expected[key] = [[k, str(v)] for k, v in sorted(Counter(r[column] for r in tables[table]).items())]
    return queries, expected


def prepare(store, settings, config, output_root, patent_root, entity_root, assignment_root, listing_policy, listing_evidence):
    release.validate_config(config)
    patent_report = read_review(store, patent_root, "curated/patent_review", config["patent_review_id"])
    entity_report = read_review(store, entity_root, "curated/patent_entity_review", config["entity_review_id"])
    assignment_report = read_review(store, assignment_root, "curated/patent_assignment_review", config["assignment_review_id"])
    release.require(entity_report["parent_review_id"] == patent_report["release_id"] and
        assignment_report["entity_review_release_id"] == entity_report["release_id"], "Mixed review releases")
    universe = verify_patent_inputs(store, patent_report)
    release.require(digest(universe) == entity_report["universe_hash"], "Entity universe mismatch")
    entries, assignment_universe, inputs = read_inputs(store, config["assignment_manifests"], allowed={"uspto_odp"}, dataset="patent_assignment_records")
    release.require(digest(universe) == digest(assignment_universe), "Assignment universe mismatch")
    release.require(all(i in inputs for i in assignment_report["inputs"]), "Assignment comparison has missing inputs")
    entities = list(read_jsonl(entity_root / "entities.jsonl"))
    comparisons = {r["observation_id"]: r for r in read_jsonl(assignment_root / "applications.jsonl")}
    release.require(set(comparisons) <= set(entries), "Unmatched assignment comparison observations")
    for oid, comparison in comparisons.items():
        release.require(comparison["source_payload_hash"] == entries[oid]["record"]["payload_hash"], "Assignment comparison payload mismatch")
    policy = load_json(listing_policy)
    listings = listing_reviews(universe, entities, policy, listing_evidence)
    reconciled = reconcile(universe, entities, listings)
    tables = {n: [] for n in SCHEMAS}
    tables["patent_listing_reviews"], tables["patent_company_reconciliation"] = listings, reconciled
    for name, row in publication_rows(read_jsonl(patent_root / "decisions.jsonl"), entities, reconciled):
        tables[name].append(row)
    release.require(len(tables["patent_publications"]) == patent_report["records"], "Publication count mismatch")
    for name, row in assignment_rows(entries, comparisons):
        tables[name].append(row)
    counts = Counter(n for r in tables["patent_publications"] for n in r["reported_company_names"])
    for entity in entities:
        chosen = next((c for c in entity["candidates"] if c["lei"] == entity["selected_lei"]), {})
        tables["patent_entity_reviews"].append({"reported_name": entity["reported_name"], "review_status": entity["status"],
            "registry_entity_id": entity["registry_entity_id"], "selected_lei": entity["selected_lei"], "legal_name": chosen.get("legal_name"),
            "jurisdiction": chosen.get("jurisdiction"), "registry_url": chosen.get("registry_url"),
            "evidence_json": release.json_text(entity["evidence"]), "candidates_json": release.json_text(entity["candidates"]),
            "historical_identity_status": "not_established", "current_ownership_status": "not_established",
            "publication_count": counts[entity["reported_name"]]})
    pubs = tables["patent_publications"]
    dates = [r["publication_date"] for r in pubs if r["publication_date"]]
    tables["patent_coverage"].append({"patent_review_id": patent_report["release_id"], "entity_review_id": entity_report["release_id"],
        "assignment_review_id": assignment_report["release_id"], "universe_hash": digest(universe),
        "coverage_note": "Bounded January 2025 publication candidates selected by company names OR technology rules, not a census. Publication authority is not company domicile. Current registry and assignment snapshots do not reconstruct historical ownership. Shared universe unchanged. Global source freshness and recurring publication are separate gaps.",
        "unresolved_listing_ids_json": release.json_text([r["listing_id"] for r in listings if r["review_status"] != "supported"]),
        "source_manifests_json": release.json_text(patent_report["inputs"] + inputs), "publications": len(pubs),
        "supported_technology_publications": sum(bool(r["supported_sector_ids"]) for r in pubs),
        "supported_name_publications": sum(r["has_supported_name_link"] for r in pubs), "assignment_applications": len(entries),
        "publication_start": min(dates) if dates else None, "publication_end": max(dates) if dates else None,
        "current_ownership_verified_records": 0, "point_in_time_eligible_records": 0})
    artifacts = {"listing-review.json": Path(listing_policy).read_bytes(), "listing-evidence/manifest.json": (listing_evidence / "manifest.json").read_bytes()}
    for info in load_json(listing_evidence / "manifest.json"):
        artifacts["listing-evidence/" + checked_key(info["file"])] = checked_body(listing_evidence / info["file"], info)
    artifacts.update({"patent-review.json": canonical_json(patent_report) + b"\n", "entity-review.json": canonical_json(entity_report) + b"\n",
        "assignment-review.json": canonical_json(assignment_report) + b"\n"})
    artifact_meta = {n: {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)} for n, b in artifacts.items()}
    release_id = digest({"version": VERSION, "arrow": pa.__version__, "config": config, "schemas": SCHEMAS,
        "artifacts": artifact_meta, "inputs": inputs, "bucket": settings.s3_bucket, "prefix": settings.s3_prefix})
    root = Path(output_root) / release_id
    root.mkdir(parents=True, exist_ok=True)
    prefix = config["curated_prefix"] + "/" + release_id
    files, ddl = {}, []
    for name, rows in tables.items():
        table = pa.Table.from_pylist(rows, schema=pa.schema([(field, release.ARROW_TYPES[kind]) for field, kind in SCHEMAS[name]]))
        relative = "tables/" + name + "/part-00000.parquet"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, path, compression="snappy", version="1.0")
        release.require(pq.ParquetFile(path).read().equals(table), "Parquet round-trip mismatch: " + name)
        body = path.read_bytes()
        location = f"s3://{settings.s3_bucket}/{settings.s3_prefix}/{prefix}/tables/{name}/"
        files[name] = {"path": relative, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "rows": len(rows), "location": location, "columns": SCHEMAS[name]}
        ddl.append(f"CREATE EXTERNAL TABLE {config['database']}.{name} ({', '.join(f'{f} {k}' for f,k in SCHEMAS[name])}) STORED AS PARQUET LOCATION '{location}';")
    for name, body in artifacts.items():
        path = root / "artifacts" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    queries, expected = validation(tables, config["database"])
    report = {"curator_version": VERSION, "catalog_owner": "patents", "workgroup_description": "Optima patent research",
        "release_id": release_id, "release_prefix": prefix, "bucket": settings.s3_bucket, "s3_prefix": settings.s3_prefix,
        "config": config, "files": files, "artifacts": artifact_meta, "expected_results": expected, "queries": queries,
        "universe_hash": digest(universe), "status": "locally_validated", "schema_version": "1.0",
        "semantics": "Reviewed publication fields and separate identity, listing-underlying, and assignment evidence. No current ownership or historical feature eligibility inferred."}
    (root / "release.json").write_bytes(canonical_json(report) + b"\n")
    (root / "tables.sql").write_text("\n\n".join(ddl) + "\n")
    (root / "queries.sql").write_text("\n\n".join("-- " + k + "\n" + v + ";" for k, v in queries.items()) + "\n")
    print(json.dumps({"directory": str(root), "expected_results": expected}), flush=True)
    return root


def publish(store, settings, root):
    root = Path(root)
    report = load_json(root / "release.json")
    release.require(report["bucket"] == settings.s3_bucket and report["s3_prefix"] == settings.s3_prefix, "Release destination mismatch")
    for name, info in report["artifacts"].items():
        checked_body(root / "artifacts" / checked_key(name), info)
    for name, info in report["artifacts"].items():
        body = checked_body(root / "artifacts" / name, info)
        key = report["release_prefix"] + "/artifacts/" + name
        write_checked(store, key, body)
        release.require(release.get_bytes(store, key) == body, "Artifact read-back mismatch")
    release.publish(store, settings, root)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=["prepare", "publish", "deploy"])
    p.add_argument("--config", type=Path, default=ROOT / "config/patent-athena.json")
    p.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    p.add_argument("--output-root", type=Path, default=ROOT / "patent-athena-build")
    p.add_argument("--listing-policy", type=Path, default=ROOT / "config/patent-listing-review.v1.json")
    p.add_argument("--listing-evidence", type=Path, default=ROOT / "reports/patent-listing-evidence-2026-09-23")
    p.add_argument("--release-dir", type=Path)
    p.add_argument("--update-existing", action="store_true")
    args = p.parse_args()
    settings = StorageSettings.load(args.storage_config)
    store = settings.store()
    config = load_json(args.config)
    if args.stage == "prepare":
        prepare(store, settings, config, args.output_root, ROOT / "patent-review-build" / config["patent_review_id"],
            ROOT / "patent-entity-build" / config["entity_review_id"], ROOT / "patent-assignment-review-build" / config["assignment_review_id"],
            args.listing_policy, args.listing_evidence)
    else:
        release.require(args.release_dir is not None, "--release-dir required")
        if args.stage == "publish":
            publish(store, settings, args.release_dir)
        else:
            release.deploy(store, settings, args.release_dir, args.update_existing)


if __name__ == "__main__":
    main()
