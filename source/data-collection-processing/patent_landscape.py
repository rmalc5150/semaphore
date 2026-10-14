#!/usr/bin/env python3
"""Normalize and classify Google Patents BigQuery JSONL exports."""

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

SECTOR_CPC = {
    "biotech": ("C12N", "C12Q", "A61K38", "A61K39", "A61P35"),
    "robotics": ("B25J", "G05D1", "G05B19"),
    "semiconductor": ("H10", "H01L", "G03F7", "C23C16"),
    "battery": ("H01M", "H01G11", "H02J7"),
}
SECTOR_TERMS = {
    "biotech": ("antibody", "biologic", "crispr", "gene editing", "nucleic acid", "rna", "vaccine"),
    "robotics": ("robot", "robotic", "manipulator", "autonomous mobile", "end effector"),
    "semiconductor": ("semiconductor", "integrated circuit", "wafer", "lithograph", "transistor", "chiplet"),
    "battery": ("battery", "electrolyte", "electrode", "energy storage", "lithium", "solid-state cell"),
}


def normalize_org(value):
    """Normalize an organization for comparison without over-aggressive stemming."""
    value = unicodedata.normalize("NFKC", value or "").casefold()
    value = " ".join("".join(c if c.isalnum() else " " for c in value).split())
    suffixes = {"inc", "incorporated", "corp", "corporation", "company", "co", "limited", "ltd", "llc", "plc", "ag", "gmbh", "se", "bv", "nv"}
    words = value.split()
    while words and words[-1] in suffixes:
        words.pop()
    return " ".join(words)


def load_companies(path):
    companies = json.loads(Path(path).read_text(encoding="utf-8"))
    for company in companies:
        names = [company["name"], *company.get("aliases", [])]
        company["normalized_aliases"] = sorted({normalize_org(name) for name in names} - {""})
    return companies


def match_companies(assignees, companies):
    normalized = {normalize_org(value) for value in (assignees or [])} - {""}
    return [c for c in companies if normalized.intersection(c["normalized_aliases"])]


def classify(record):
    text = " ".join((record.get("title") or "", record.get("abstract") or "")).casefold()
    codes = [re.sub(r"[ /]", "", code.upper()) for code in record.get("cpc_codes", [])]
    results = []
    for sector in SECTOR_CPC:
        cpc_hits = sorted({prefix for prefix in SECTOR_CPC[sector] if any(code.startswith(prefix) for code in codes)})
        term_hits = sorted({term for term in SECTOR_TERMS[sector] if term in text})
        score = min(1.0, 0.65 * bool(cpc_hits) + 0.20 * min(len(term_hits), 2) + 0.15 * bool(cpc_hits and term_hits))
        if score:
            results.append({"sector": sector, "confidence": round(score, 2), "cpc_hits": cpc_hits, "term_hits": term_hits})
    return sorted(results, key=lambda item: (-item["confidence"], item["sector"]))


def process(records, companies):
    output = []
    for record in records:
        matches = match_companies(record.get("assignees"), companies)
        if not matches and record.get("matched_company"):
            matches = [c for c in companies if c["name"] == record["matched_company"]]
        classifications = classify(record)
        for company in matches:
            row = dict(record)
            row["matched_company"] = company["name"]
            row["company_sector"] = company["sector"]
            row["technology_classifications"] = classifications
            row["target_sector_match"] = any(x["sector"] == company["sector"] for x in classifications)
            row["review_required"] = not any(x["sector"] == company["sector"] and x["confidence"] >= 0.65 for x in classifications)
            output.append(row)
    return output


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="BigQuery newline-delimited JSON export")
    parser.add_argument("--companies", default=str(Path(__file__).with_name("patent_pilot_companies.json")))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    rows = process(read_jsonl(args.input), load_companies(args.companies))
    with Path(args.output).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    counts = Counter(row["company_sector"] for row in rows)
    print(json.dumps({"records": len(rows), "by_company_sector": counts}, default=dict))


if __name__ == "__main__":
    main()
