#!/usr/bin/env python3
"""Build the controller's source lookup from the saved inventory and operational evidence."""
import argparse
from collections import defaultdict
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT.parent / "data-source-overview.txt"
OUTPUT = ROOT / "config/key.registry.json"
CONTROLLER = "i-070bab0b09f794629"
SHARED_PATH = "/srv/optima/key.registry.json"
HEADER = re.compile(r"^(\d{3}|D\d{2}) (.+?) \[([^\]\n]+)\] *$", re.M)
PROFILE = r"ME-\d{2}@\d+\.\d+\.\d+"
DAY = r"\d{4}-\d{2}-\d{2}"
INGEST = re.compile(r"(?:^|/)source=([^/]+)/dataset=([^/]+)/ingestion_date=(" + DAY + r")(?:/|$)")
USPTO_DATASETS = {
    "040": {"patent_records", "patent_assignment_records"},
    "063": {"patent_office_actions"},
    "064": {"patent_petition_decisions"},
}
# Shared modules documented in raw_parsers/README.md. A module here is an
# implemented reader, not a claim that every collection used that reader.
SHARED_READERS = {
    "022": "canada_noc", "023": "chictr_tables", "024": "nmpa_tables",
    "021": "pmda_tables", "025": "pubmed_enrichment", "027": "epmc_fulltext",
}

def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))

def raw_formats(description):
    if description.startswith("None "):
        return []
    forms = {
        "jats_xml": r"\bJATS\b",
        "xbrl_json": r"\bXBRL JSON\b",
        "sdmx_csv": r"\bSDMX[- ]CSV\b",
        "sdmx_xml": r"\bSDMX[- ]XML\b",
        "geojson": r"\bGeoJSON\b",
        "rdf_xml": r"\bRDF/XML\b",
        "sec_submission_text": r"\b(SEC Form 6-K submission text|SEC EDGAR complete .* filing text)\b",
        "jsonl": r"\bJSONL\b",
        "json": r"\bJSON\b",
        "xml": r"\bXML\b",
        "html": r"\bHTML\b",
        "pdf": r"\bPDFs?\b",
        "csv": r"\bCSVs?\b",
        "tsv": r"\bTSVs?\b",
        "excel": r"\b(?:Excel|XLSX?|workbooks?)\b",
        "zip": r"\bZIPs?\b",
        "gzip": r"\b(?:gzip|gzipped)\b",
        "7z": r"\b7z\b",
        "mrt": r"\bMRT\b",
        "netcdf": r"\bNetCDF\b",
        "rds": r"\bRDS\b",
        "sas_transport": r"\bSAS transport\b",
        "ascii_text": r"\bASCII\b",
    }
    found = {}
    for name, pattern in forms.items():
        match = re.search(pattern, description, re.I)
        if match:
            found[name] = match.start()
    for child, parent in {"jats_xml": "xml", "xbrl_json": "json", "sdmx_csv": "csv",
                          "sdmx_xml": "xml", "rdf_xml": "xml"}.items():
        if child in found:
            found.pop(parent, None)
    return sorted(found, key=found.get)

def publication_date(value):
    m = re.match(r"(\d{4}(?:-\d{2}){0,2})(?: (\d{2}:\d{2}:\d{2}) UTC)?(?:\b|$)", value)
    if not m:
        return {"value": None, "precision": None, "status": "unverified", "inventory_value": value}
    precision = {4: "year", 7: "month", 10: "day"}[len(m[1])]
    return {"value": f"{m[1]}T{m[2]}Z" if m[2] else m[1],
            "precision": "second" if m[2] else precision, "status": "recorded", "inventory_value": value}

def count(text, pattern):
    m = re.search(r"(\d[\d,]*) " + pattern, text or "", re.I)
    return int(m[1].replace(",", "")) if m else None

def athena_status(inventory, grouped, labelled, grouped_snapshot, queue):
    committed = count(inventory, r"committed rows?\b")
    files = count(inventory, r"file-inventory rows?\b")
    group_rows = count(grouped, r"rows?\b")
    labelled_rows = count(labelled, r"rows?\b")
    # All numeric views are kept independently. In particular a file inventory
    # entry is not proof of published data rows or of semiotic publication.
    if (committed or 0) > 0 or (group_rows or 0) > 0 or (
        inventory and re.search(r"\b[1-9][\d,]* (?:(?!file-inventory\b)[\w-]+ ){0,5}(?:rows?|records?|lines)\b", inventory)
    ):
        status = "published_rows_reported"
    elif (labelled_rows or 0) > 0:
        status = "metadata_receipt_reported"
    elif (files or 0) > 0:
        status = "artifact_inventory_only_reported"
    elif committed == 0 or group_rows == 0 or (inventory and inventory.startswith("0 ")):
        status = "no_rows_in_checked_views"
    else:
        status = "not_verified"
    return {"status": status, "committed_rows": committed, "committed_batch_files": count(inventory, r"batch files?\b"),
            "artifact_inventory_rows": files, "distinct_originals": count(inventory, r"distinct originals?\b"),
            "inventory_snapshot": inventory, "grouped_metadata_snapshot": grouped,
            "grouped_metadata_rows": group_rows, "grouped_metadata_partitions": count(grouped, r"job partitions?\b"),
            "grouped_source_key_readback": grouped_snapshot, "metadata_receipt_snapshot": labelled,
            "metadata_queue": {"inventory_value": queue,
                "outstanding_inputs": count(queue, r"outstanding input files?\b"),
                "raw_validation_failures": count(queue, r"with raw-validation failures?\b")},
            "combined_semiotic_publication": "not_established_by_inventory"}

def verified_batches(cache):
    result = defaultdict(lambda: defaultdict(set))
    for path, evidence in cache.items():
        m = INGEST.search(path)
        if m and evidence.get("sha256") and evidence.get("verified_at") and evidence.get("records", 0) > 0:
            result[m[1]][m[2]].add(date.fromisoformat(m[3]).isoformat())
    return result

def build(inventory=INVENTORY):
    raw = inventory.read_bytes()
    text = raw.decode("utf-8")
    entries = list(HEADER.finditer(text))
    if not entries:
        raise ValueError("Empty inventory")
    profiles = {}
    for m in re.finditer(rf"^({PROFILE}) \| (.*?) — (.+)$", text[:entries[0].start()], re.M):
        if m[1] in profiles:
            raise ValueError(f"Duplicate version {m[1]}")
        profiles[m[1]] = {"title": m[2], "routing_rule": m[3], "deployment_status": "not_verified"}
    runtime = load("config/metadata-engine.json")
    grouped = load("state/metadata-publication-counts.athena.json")
    receipt = load("state/metadata-publication-counts.json")
    registered = load("config/constellation-source-registry.json")
    registered_by_id = {str(x["catalog_entry"]).zfill(3): x for x in registered["sources"]}
    pilots = load("config/semiotic-pilot-v1.2.json")
    pilots_by_id = {x["catalog_id"]: x for x in pilots["sources"]}
    batches = verified_batches(load("state/collection-health/health-verified-batches.json"))
    sources = {}
    index = defaultdict(list)
    for n, m in enumerate(entries):
        source_id, name, source_key = m.groups()
        if source_id in sources:
            raise ValueError(f"Duplicate source ID {source_id}")
        fragment = text[m.end():entries[n+1].start() if n+1 < len(entries) else len(text)]
        fields = {}
        for label, value in re.findall(r"^    (Athena grouped) +(.+)$", fragment, re.M):
            fields[label] = value
        for label, value in re.findall(r"^    (\S.*?)[ ]{2,}(\S.*)$", fragment, re.M):
            fields[label] = value
        route = fields["Metadata version"]
        version = route.split()[0]
        suffix = route.partition(" (")[2].removesuffix(")")
        refs = [p.split("@")[0] for p in profiles]
        alternatives = list(dict.fromkeys(re.findall(r"\bME-\d{2}\b", suffix)))
        if version not in profiles or set(alternatives) - set(refs):
            raise ValueError(f"Unknown profile for {source_id}: {route}")
        parser = runtime["contracts"].get(source_key)
        parser = ({k: parser[k] for k in
                  ("adapter", "adapter_version", "contract_version", "record_kind", "state") if k in parser}
                  if parser is not None else None)
        pilot = pilots_by_id.get(source_id)
        pilot = ({"configuration": pilots["version"], "profile_version": pilot["profile_version"],
                  "input_kind": pilot["input_kind"], "status": pilot["profile_status"]}
                 if pilot and pilot["source_key"] == source_key else None)
        date_map = batches.get(source_key, {})
        if source_id in USPTO_DATASETS:
            date_map = {k: v for k, v in date_map.items() if k in USPTO_DATASETS[source_id]}
        observed_dates = sorted({day for days in date_map.values() for day in days})
        entry = registered_by_id.get(source_id, {})
        datasets = entry.get("datasets", []) if entry.get("source_key") == source_key else []
        urls = [fields[k] for k in sorted(fields) if re.fullmatch(r"Raw evidence \d+", k)]
        desc = fields["Raw file description"]
        snap = grouped["sources"].get(source_key)
        sources[source_id] = {
            "name": name, "source_key": source_key, "registered_datasets": datasets,
            "metadata_version": {"target_profile_id": version,
                "assignment_status": "provisional" if "provisional route" in suffix else "assigned",
                "routing_note": suffix or None, "secondary_profile_ids": [p for p in profiles if p.split("@")[0] in alternatives],
                "configured_metadata_engine_version": runtime["version"] if parser else None,
                "semiotic_pilot_profile": pilot},
            "raw_format_parser": {"configured_ingest_adapter": parser,
                "known_shared_parser_module": f"raw_parsers.{SHARED_READERS[source_id]}" if source_id in SHARED_READERS else None,
                "sample_formats_mentioned": raw_formats(desc),
                "sample_description": desc, "verified_raw_examples": urls,
                "combined_parser_execution": "not_verified"},
            "collection": {"daily_route": fields.get("Daily"), "monthly_route": fields.get("Monthly"),
                "historical_route": fields["Historical"], "verified_ingestion_dates_utc": observed_dates,
                "first_verified_ingestion_date_utc": observed_dates[0] if observed_dates else None,
                "last_verified_ingestion_date_utc": observed_dates[-1] if observed_dates else None,
                "verified_dates_by_dataset": {k: sorted(v) for k, v in sorted(date_map.items())},
                "date_status": "partial_verified_batch_history" if observed_dates else "not_in_verified_batch_cache"},
            "first_raw_publication": publication_date(fields["First raw publication"]),
            "athena_publication": athena_status(fields.get("Athena"), fields.get("Athena grouped"),
                    fields.get("Labelled"), {"scope": "source_key", **snap} if snap else None, fields["Metadata"]),
        }
        index[source_key].append(source_id)
    return {
        "schema_version": "1.0.0",
        "controller_instance_id": CONTROLLER,
        "controller_shared_path": SHARED_PATH,
        "source_count": len(sources),
        "provenance": {
            "source_inventory": inventory.name, "source_inventory_sha256": sha256(raw).hexdigest(),
            "metadata_contracts": "config/metadata-engine.json", "semiotic_pilots": "config/semiotic-pilot-v1.2.json",
            "collection_date_basis": "Verified raw batch ingestion_date partitions. Partial cache, not historic coverage or publisher dates.",
            "collection_date_cache": "state/collection-health/health-verified-batches.json",
            "athena_committed_inventory_as_of": re.search(r"^Committed Athena verification (.+)$", text, re.M)[1],
            "athena_grouped_readback_as_of": grouped["as_of"], "athena_grouped_query_execution_id": grouped["query_execution_id"],
            "metadata_receipts_as_of": receipt["receipts"]["as_of"],
            "athena_status_scope": "Saved observations from multiple snapshots. Counts can overlap. Shared source-key counts must not be summed across catalogue IDs.",
        },
        "metadata_profiles_by_id": profiles, "sources_by_id": sources,
        "source_ids_by_key": dict(sorted(index.items())),
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inventory", type=Path, default=INVENTORY)
    p.add_argument("--output", type=Path, default=OUTPUT)
    p.add_argument("--check", action="store_true", help="Verify that the existing registry matches the current inputs.")
    args = p.parse_args()
    data = json.dumps(build(args.inventory), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.check:
        if args.output.read_text(encoding="utf-8") != data:
            p.exit(1, "Registry is out of date. Build it again.\n")
        return
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output.parent, delete=False) as temporary:
        temporary.write(data)
        temp = Path(temporary.name)
    try:
        temp.chmod(0o644)
        os.replace(temp, args.output)
    finally:
        temp.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
