#!/usr/bin/env python3
"""Corroborate a bounded patent-party cohort with reproducible GLEIF evidence.

This creates a registry crosswalk, not a replacement company universe or a
determination of patent title. Source names and unresolved alternatives survive.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import time

from collection_storage import StorageSettings, now, write_checked
from patent_query_plan import normalized_name
from research_contract import ROOT, canonical_json, digest, load_json

VERSION = "patent-entity-review-1.0"
API = "https://api.gleif.org/api/v1/lei-records"
# Expand only terminal legal-form tokens, never substantive company words.
FORMS = {"co": "company", "ltd": "limited", "corp": "corporation", "inc": "incorporated"}
SUFFIXES = set(FORMS) | set(FORMS.values()) | {"ag", "se", "sa", "plc", "llc"}
QUERY_HINTS = {"TAIWAN SEMICONDUCTOR MFG CO LTD": "Taiwan Semiconductor",
               "NINGDE CONTEMPORARY AMPEREX TECH CO LTD": "Contemporary Amperex",
               "PANASONIC IP MAN CO LTD": "Panasonic Intellectual Property"}


def name_key(name):
    words = normalized_name(name).split()
    pos = len(words)
    while pos and words[pos - 1] in SUFFIXES:
        pos -= 1
    return " ".join(words[:pos] + [FORMS.get(w, w) for w in words[pos:]])


def search_term(name):
    if name in QUERY_HINTS:
        return QUERY_HINTS[name]
    words = normalized_name(name).split()
    while words and words[-1] in SUFFIXES:
        words.pop()
    return " ".join(words)


def checked_body(path, meta):
    body = Path(path).read_bytes()
    if hashlib.sha256(body).hexdigest() != meta["sha256"] or len(body) != meta["bytes"]:
        raise ValueError("Evidence checksum mismatch: " + str(path))
    return body


def put_local(root, filename, body):
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != body:
        raise ValueError("Immutable artifact conflict: " + str(path))
    path.write_bytes(body)
    return {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}


def fetch(review_root, output, limit=20, session=None):
    import requests
    if not 1 <= limit <= 100:
        raise ValueError("Cohort limit must be 1..100")
    review_root, output = Path(review_root), Path(output)
    report = load_json(review_root / "review.json")
    queue = [json.loads(line) for line in checked_body(review_root / "company-review-queue.jsonl",
        report["files"]["company-review-queue.jsonl"]).splitlines()]
    names = list(dict.fromkeys(q["reported_name"] for q in queue))[:limit]
    scope = {"version": VERSION, "parent_review_id": report["release_id"], "names": names,
             "queries": {n: search_term(n) for n in names}}
    output.mkdir(parents=True, exist_ok=True)
    path = output / "fetch.json"
    manifest = load_json(path) if path.exists() else {"scope": scope, "observed_at": now(), "queries": [], "status": "partial"}
    if manifest["scope"] != scope:
        raise ValueError("Fetch directory belongs to another cohort")
    for q in manifest["queries"]:
        checked_body(output / q["file"], q)
    session = session or requests.Session()
    session.headers.update({"User-Agent": "Optima Holdings support@optima-holdings.com"})
    completed = {q["reported_name"] for q in manifest["queries"]}
    for name in names:
        if name in completed:
            continue
        term = search_term(name)
        # Fetch up to 200 alternatives. Truncation blocks a unique match below.
        for attempt in range(4):
            response = session.get(API, params={"filter[entity.names]": term, "page[size]": 200}, timeout=45)
            if response.status_code not in {429, 500, 502, 503, 504}:
                break
            time.sleep(2 ** attempt)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data.get("data"), list):
            raise ValueError("Invalid GLEIF response")
        filename = "evidence/" + hashlib.sha256(response.content).hexdigest() + ".json"
        metadata = put_local(output, filename, response.content)
        manifest["queries"].append({"reported_name": name, "query": term, "source_url": response.url,
            "observed_at": now(), "file": filename, **metadata})
        path.write_bytes(canonical_json(manifest) + b"\n")
        print(json.dumps({"name": name, "candidates": len(data["data"])}), flush=True)
        time.sleep(.15)
    manifest["status"] = "complete"
    path.write_bytes(canonical_json(manifest) + b"\n")
    return manifest


def candidate(attrs, reported):
    entity, registration = attrs["entity"], attrs["registration"]
    names = [{**entity["legalName"], "type": "LEGAL_NAME"}]
    names += entity.get("otherNames", []) + entity.get("transliteratedOtherNames", [])
    matches = [n for n in names if name_key(n["name"]) == name_key(reported)]
    # Previous/trading names do not establish a current legal-name link.
    current = [n for n in matches if n.get("type") in {
        "LEGAL_NAME", "ALTERNATIVE_LANGUAGE_LEGAL_NAME", "PREFERRED_ASCII_TRANSLITERATED_LEGAL_NAME",
        "AUTO_ASCII_TRANSLITERATED_LEGAL_NAME"}]
    return {"lei": attrs["lei"], "legal_name": entity["legalName"]["name"],
        "jurisdiction": entity.get("jurisdiction"), "legal_address": entity.get("legalAddress"),
        "registered_at": entity.get("registeredAt"), "registered_as": entity.get("registeredAs"),
        "entity_status": entity.get("status"), "registration_status": registration.get("status"),
        "corroboration_level": registration.get("corroborationLevel"),
        "last_update_date": registration.get("lastUpdateDate"), "matched_names": matches,
        "current_name_match": bool(current),
        "eligible": bool(current) and entity.get("status") == "ACTIVE"
            and registration.get("status") == "ISSUED"
            and registration.get("corroborationLevel") == "FULLY_CORROBORATED",
        "registry_url": API + "/" + attrs["lei"]}


def resolve(name, data):
    candidates = [candidate(r["attributes"], name) for r in data["data"]]
    matches = {c["lei"]: c for c in candidates if c["matched_names"]}
    total = data.get("meta", {}).get("pagination", {}).get("total")
    complete = isinstance(total, int) and total == len(candidates) and not data.get("links", {}).get("next")
    # Include lapsed, previous-name and foreign-jurisdiction conflicts in the
    # ambiguity check; never pick the first active name from competing LEIs.
    selected = next(iter(matches.values())) if complete and len(matches) == 1 else None
    if selected and not selected["eligible"]:
        selected = None
    status = ("registry_name_supported" if selected else "search_incomplete" if not complete
              else "ambiguous_registry_name" if len(matches) > 1 else "registry_status_or_name_review" if matches
              else "no_exact_registry_name")
    return {"reported_name": name, "status": status, "selected_lei": selected["lei"] if selected else None,
        "candidates": candidates, "search_complete": complete,
        "historical_identity_status": "not_established", "current_ownership_status": "not_established"}


def build(review_root, evidence_root, output_root, universe, per_entity=3):
    review_root, evidence_root = Path(review_root), Path(evidence_root)
    parent, fetch_manifest = load_json(review_root / "review.json"), load_json(evidence_root / "fetch.json")
    if fetch_manifest["status"] != "complete" or fetch_manifest["scope"]["parent_review_id"] != parent["release_id"]:
        raise ValueError("Incomplete or unrelated registry evidence")
    if digest(universe) != parent["universe_hash"] or not 1 <= per_entity <= 10:
        raise ValueError("Universe or cohort bound mismatch")
    names = fetch_manifest["scope"]["names"]
    if len(fetch_manifest["queries"]) != len(names) or set(names) != {q["reported_name"] for q in fetch_manifest["queries"]}:
        raise ValueError("Missing/duplicate registry queries")
    rows = []
    for query in fetch_manifest["queries"]:
        data = json.loads(checked_body(evidence_root / query["file"], query))
        rows.append({**resolve(query["reported_name"], data), "evidence": query})
    by_name = {normalized_name(r["reported_name"]): r for r in rows}
    by_lei = defaultdict(set)
    for identifier in universe["external_identifiers"]:
        if identifier["system"] == "lei" and identifier["review_status"] == "verified":
            by_lei[identifier["value"]].add(identifier["entity_id"])
    for row in rows:
        ids = sorted(by_lei[row["selected_lei"]]) if row["selected_lei"] else []
        row["universe_company_ids_by_verified_lei"] = ids
        row["universe_action"] = "existing_verified_identifier" if len(ids) == 1 else "identifier_conflict" if ids else "entity_review_required"
        # A LEI-scoped identity is stable without silently inventing or merging
        # the shared universe's company IDs, listing IDs, or aliases.
        row["registry_entity_id"] = "lei:" + row["selected_lei"] if row["selected_lei"] else None
    release_id = digest({"version": VERSION, "parent": parent["release_id"], "fetch": fetch_manifest,
                         "universe": digest(universe), "per_entity": per_entity})
    root = Path(output_root) / release_id
    root.mkdir(parents=True, exist_ok=True)
    source = checked_body(review_root / "decisions.jsonl", parent["files"]["decisions.jsonl"])
    selected_apps, application_counts, publication_counts = {}, Counter(), Counter()
    linked = reviewed = additional = 0
    output_lines = []
    for line in source.splitlines():
        decision = json.loads(line)
        parties = []
        for party in decision["reported_parties"]:
            row = by_name.get(normalized_name(party["reported_name"]))
            if row:
                parties.append({"reported_name": party["reported_name"], "role": party["role"],
                    "status": row["status"], "registry_entity_id": row["registry_entity_id"],
                    "original_candidate_company_ids": party["candidate_company_ids"]})
        if not parties:
            continue
        reviewed += 1
        leis = sorted({p["registry_entity_id"] for p in parties if p["registry_entity_id"]})
        linked += bool(leis)
        additional += bool(leis) and not bool(decision["reported_party_company_ids"])
        publication_counts.update(leis)
        output_lines.append(canonical_json({"observation_id": decision["observation_id"],
            "publication_number": decision["publication_number"], "application_number": decision["application_number"],
            "publication_date": decision["publication_date"], "parties": parties,
            "registry_entity_ids": leis, "historical_identity_status": "not_established",
            "current_ownership_status": "not_established", "point_in_time_eligible": False}) + b"\n")
        match = re.fullmatch(r"US-\d{4}(\d{8})-A", decision.get("application_number") or "")
        if match and leis and (decision.get("publication_number") or "").startswith("US-"):
            number = match[1]
            if number not in selected_apps and any(application_counts[lei] < per_entity for lei in leis):
                selected_apps[number] = {"application_number": number, "publication_number": decision["publication_number"],
                    "registry_entity_ids": leis, "reported_names": [p["reported_name"] for p in parties if p["registry_entity_id"]]}
                application_counts.update(leis)
    files = {}
    files["entities.jsonl"] = put_local(root, "entities.jsonl", b"".join(canonical_json(r) + b"\n" for r in rows))
    files["publication-links.jsonl"] = put_local(root, "publication-links.jsonl", b"".join(output_lines))
    files["assignment-cohort.json"] = put_local(root, "assignment-cohort.json", canonical_json(list(selected_apps.values())) + b"\n")
    files["fetch.json"] = put_local(root, "fetch.json", canonical_json(fetch_manifest) + b"\n")
    for query in fetch_manifest["queries"]:
        files[query["file"]] = put_local(root, query["file"], checked_body(evidence_root / query["file"], query))
    report = {"version": VERSION, "release_id": release_id, "parent_review_id": parent["release_id"],
        "universe_hash": digest(universe), "name_status_counts": dict(Counter(r["status"] for r in rows)),
        "reviewed_names": len(rows), "reviewed_publications": reviewed, "registry_linked_publications": linked,
        "additional_registry_linked_publications": additional, "publications_by_registry_entity": dict(publication_counts),
        "assignment_cohort_applications": len(selected_apps), "current_ownership_verified_records": 0,
        "shared_universe_updated": False, "athena_status": "not_published", "files": files}
    put_local(root, "review.json", canonical_json(report) + b"\n")
    return root, report


def publish(root, store):
    root = Path(root)
    report = load_json(root / "review.json")
    prefix = "curated/patent_entity_review/" + report["release_id"]
    for name, meta in report["files"].items():
        body = checked_body(root / name, meta)
        write_checked(store, prefix + "/" + name, body,
                      content_type="application/x-ndjson" if name.endswith("jsonl") else "application/json")
    write_checked(store, prefix + "/review.json", (root / "review.json").read_bytes())
    return prefix


def main():
    from research_contract import COLLECTION_UNIVERSE
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=["fetch", "build", "publish"])
    p.add_argument("--review-root", type=Path)
    p.add_argument("--evidence-root", type=Path)
    p.add_argument("--output-root", type=Path, default=ROOT / "patent-entity-build")
    p.add_argument("--release-root", type=Path)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--per-entity", type=int, default=3)
    p.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    a = p.parse_args()
    if a.stage == "fetch":
        fetch(a.review_root, a.evidence_root, a.limit)
    elif a.stage == "build":
        root, report = build(a.review_root, a.evidence_root, a.output_root, load_json(COLLECTION_UNIVERSE), a.per_entity)
        print(json.dumps({"directory": str(root), **{k:v for k,v in report.items() if k != "files"}}))
    else:
        print(publish(a.release_root, StorageSettings.load(a.storage_config).store()))


if __name__ == "__main__":
    main()
