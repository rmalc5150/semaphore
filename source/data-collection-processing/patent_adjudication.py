#!/usr/bin/env python3
"""Create reproducible, evidence-supported patent decisions and specific review queues."""
import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from collection_storage import StorageSettings, now, write_checked, write_json
from patent_collection import PatentMatcher
from patent_query_plan import normalized_name
from regulatory_athena import read_inputs
from research_contract import ROOT, canonical_json, digest, load_json
from sec_athena_pilot import get_bytes, require

POLICY_PATH = ROOT / "config/patent-review-policy.v1.json"
VERSION = "patent-adjudication-1.0"


class Reviewer:
    def __init__(self, universe, policy):
        self.universe, self.policy = universe, policy
        self.matcher = PatentMatcher(universe)
        self.companies = self.matcher.companies
        self.strict, self.aliases = defaultdict(set), defaultdict(list)
        for cid, company in self.companies.items():
            self.strict[normalized_name(company["canonical_name"])].add(cid)
        for alias in universe["company_aliases"]:
            if alias["review_status"] == "verified" and alias["company_id"] in self.companies:
                self.aliases[normalized_name(alias["alias"])].append(alias)
        self.registry = defaultdict(list)
        for identifier in universe["external_identifiers"]:
            if identifier["review_status"] == "verified" and identifier["system"] in {"lei", "cik", "sec_cik"}:
                self.registry[identifier["entity_id"]].append(identifier)

    def party(self, name, role, publication_date):
        key = normalized_name(name)
        ids, _ = self.matcher.match([name])
        strict = set(self.strict.get(key, ())) if key else set()
        alias_evidence = defaultdict(list)
        for alias in self.aliases.get(key, ()):
            # Only explicit historical bounds can corroborate a historical alias.
            if publication_date and alias["valid_from"] and alias["valid_from"] <= publication_date and (
                    alias["valid_to"] is None or publication_date < alias["valid_to"]):
                strict.add(alias["company_id"])
                alias_evidence[alias["company_id"]].append(alias)
        eligible = sorted(cid for cid in strict if self.companies[cid]["review_status"] == "verified"
            and self.companies[cid]["entity_type"] == "legal_entity" and self.registry[cid])
        selected = eligible[0] if len(eligible) == 1 else None
        if selected:
            status, reason = "registry_name_supported", "exact_name_of_unique_registry_verified_legal_entity"
        elif len(eligible) > 1 or len(ids) > 1:
            status, reason = "ambiguous", "multiple_company_entities_require_identifier_reconciliation"
        elif ids:
            status, reason = "pending", "company_identity_or_alias_not_verified"
        else:
            status, reason = "unresolved", "assignee_not_in_company_universe"
        return {"reported_name": name, "role": role, "status": status, "reason": reason,
            "company_id": selected, "candidate_company_ids": ids,
            "registry_identifiers": self.registry[selected] if selected else [],
            "identity_evidence": self.companies[selected]["evidence"] if selected else [],
            "alias_evidence": alias_evidence[selected] if selected else [],
            "historical_identity_status": "not_established", "current_ownership_status": "not_established",
            "company_sector_memberships": [s for s in self.companies[selected]["sectors"] if s["review_status"] == "verified"] if selected else []}

    def sectors(self, record):
        data = record["payload"]["data"]
        codes = sorted({re.sub(r"\s", "", c.upper()) for c in data.get("cpc_codes", [])})
        supported = []
        for rule in self.policy["rules"]:
            hits = [c for c in codes if any(c.startswith(p) for p in rule["cpc_prefixes"])
                    and not any(c.startswith(p) for p in rule.get("exclude_prefixes", []))]
            if hits:
                supported.append({"sector_id": rule["sector_id"], "category": rule["category"],
                    "status": "supported", "basis": "source_cpc_and_reviewed_sector_mapping",
                    "cpc_codes": hits, "definition_sources": rule["source_urls"]})
        categories = {r["category"] for r in supported}
        pending = [dict(r, reason="discovery_rule_requires_more_specific_cpc_or_document_review")
                   for r in record["payload"].get("technology_classifications", []) if r["category"] not in categories]
        return supported, pending

    def decide(self, record):
        data = record["payload"]["data"]
        parties = [self.party(n, role, data.get("publication_date"))
            for field, role in (("assignees", "publication_assignee"), ("applicants", "applicant"))
            for n in data.get(field, [])]
        supported, pending = self.sectors(record)
        reasons = sorted({p["reason"] for p in parties if p["status"] != "registry_name_supported"})
        if not parties:
            reasons.append("no_reported_assignee_or_applicant")
        if pending or not supported:
            reasons.append("technology_document_review_needed")
        # Ownership is independent, so it cannot turn a supported technology
        # record back into one opaque, all-purpose review_required flag.
        return {"record_id": record["record_id"], "observation_id": record["observation_id"],
            "source": record["source"], "source_record_id": record["source_record_id"],
            "publication_number": data.get("publication_number"), "application_number": data.get("application_number"),
            "publication_date": data.get("publication_date"), "title": data.get("title"),
            "source_url": record["source_url"], "source_payload_hash": record["payload_hash"],
            "source_evidence": record["payload"]["source_evidence"],
            "reported_parties": parties, "supported_technology": supported, "pending_technology": pending,
            "research_sector_ids": sorted({x["sector_id"] for x in supported}),
            "reported_party_company_ids": sorted({p["company_id"] for p in parties if p["company_id"]}),
            "current_owner_company_ids": [], "current_ownership_status": "assignment_history_not_verified",
            "review_reasons": sorted(set(reasons)), "point_in_time_eligible": False}


def prepare(store, manifests, output_root, policy=None):
    policy = policy or load_json(POLICY_PATH)
    entries, universe, inputs = read_inputs(store, manifests,
        allowed={"google_patents_bigquery", "uspto_odp"}, dataset="patent_records")
    release_id = digest({"version": VERSION, "policy": policy, "universe": digest(universe), "inputs": inputs})
    root = Path(output_root) / release_id
    root.mkdir(parents=True, exist_ok=True)
    reviewer = Reviewer(universe, policy)
    sectors, categories, party_statuses, reasons = (Counter() for _ in range(4))
    queue = {}
    supported_count = linked_count = 0
    files = {}
    path = root / "decisions.jsonl"
    with path.open("wb") as handle:
        for entry in entries.values():
            decision = reviewer.decide(entry["record"])
            handle.write(canonical_json(decision) + b"\n")
            sectors.update(decision["research_sector_ids"])
            categories.update({x["category"] for x in decision["supported_technology"]})
            reasons.update(decision["review_reasons"])
            supported_count += bool(decision["research_sector_ids"])
            linked_count += bool(decision["reported_party_company_ids"])
            for party in decision["reported_parties"]:
                party_statuses[party["status"]] += 1
                if party["status"] == "registry_name_supported":
                    continue
                key = (normalized_name(party["reported_name"]), party["role"], party["reason"])
                q = queue.setdefault(key, {"reported_name": party["reported_name"], "role": party["role"],
                    "reason": party["reason"], "candidate_company_ids": set(), "publication_count": 0, "examples": []})
                q["candidate_company_ids"].update(party["candidate_company_ids"])
                q["publication_count"] += 1
                if len(q["examples"]) < 3:
                    q["examples"].append({"publication_number": decision["publication_number"], "source_url": decision["source_url"]})
    qrows = [{**q, "candidate_company_ids": sorted(q["candidate_company_ids"])} for q in queue.values()]
    qrows.sort(key=lambda q: (-q["publication_count"], q["reported_name"], q["role"]))
    with (root / "company-review-queue.jsonl").open("wb") as handle:
        for row in qrows:
            handle.write(canonical_json(row) + b"\n")
    (root / "policy.json").write_bytes(canonical_json(policy) + b"\n")
    for filename in ("decisions.jsonl", "company-review-queue.jsonl", "policy.json"):
        body = (root / filename).read_bytes()
        files[filename] = {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
    report = {"status": "evidence_reviewed_with_explicit_gaps", "release_id": release_id,
        "version": VERSION, "universe_hash": digest(universe), "policy_hash": digest(policy), "inputs": inputs,
        "records": len(entries), "records_with_supported_technology": supported_count,
        "records_with_registry_name_links": linked_count, "supported_sector_counts": dict(sectors),
        "supported_category_counts": dict(categories), "reported_party_statuses": dict(party_statuses),
        "review_reason_counts": dict(reasons), "company_queue_groups": len(qrows),
        "current_ownership_verified_records": 0, "point_in_time_eligible_records": 0,
        "athena_status": "not_published", "files": files}
    (root / "review.json").write_bytes(canonical_json(report) + b"\n")
    return root, report


def publish(store, root):
    root = Path(root)
    report = load_json(root / "review.json")
    prefix = "curated/patent_review/" + report["release_id"]
    for name, meta in report["files"].items():
        body = (root / name).read_bytes()
        require(hashlib.sha256(body).hexdigest() == meta["sha256"], "Review file checksum mismatch")
        write_checked(store, prefix + "/" + name, body, content_type="application/x-ndjson" if name.endswith("jsonl") else "application/json")
    write_json(store, prefix + "/review.json", report)
    return prefix


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", action="append", required=True)
    p.add_argument("--storage-config", type=Path, default=ROOT / "config/collection-storage.s3.json")
    p.add_argument("--output-root", type=Path, default=ROOT / "patent-review-build")
    p.add_argument("--publish", action="store_true")
    args = p.parse_args()
    store = StorageSettings.load(args.storage_config).store()
    root, report = prepare(store, args.manifest, args.output_root)
    if args.publish:
        report = {**report, "s3_prefix": publish(store, root)}
    print(json.dumps({"directory": str(root), **report}))


if __name__ == "__main__":
    main()
