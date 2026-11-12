"""Reproduce the UK/Japan sample pilot against official sources without S3 writes."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

from collection_storage import LocalStore
from regulatory_collection import EvidenceClient
from mhra_product_enrichment import enrich
from japan_pmda_designations import SOURCE_URL, parse_pdf


def samples(path):
    with open(path, newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    unique = {}
    for row in rows:
        unique[row["provider_id"]] = {**row, "payload": json.loads(row["payload_json"])}
    return rows, list(unique.values())


def write_review_csv(output, uk, japan):
    with (Path(output) / "sample-results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "provider_id", "product", "source_organisations",
            "roles", "status", "source_page", "approval_date", "cancellation_date", "name_review_required"])
        writer.writeheader()
        for source, rows in (("uk_mhra", uk), ("japan_pmda", japan)):
            for row in rows:
                data = row["enrichment"]
                relationships = data["companyRelationships"]
                writer.writerow({"source": source, "provider_id": row["provider_id"],
                    "product": row.get("title", data.get("designatedProductName")),
                    "source_organisations": " | ".join(dict.fromkeys(r["name"] for r in relationships)),
                    "roles": " | ".join(dict.fromkeys(r["role"] for r in relationships)),
                    "status": data.get("status", data.get("designationStatus")), "source_page": data.get("sourcePage"),
                    "approval_date": data.get("approvalDate"), "cancellation_date": data.get("cancellationDate"),
                    "name_review_required": data.get("applicantNameReviewRequired", False)})


class ReplayClient(EvidenceClient):
    """Re-evaluate parsing against saved responses, retaining original retrieval times."""
    def __init__(self, store, source, evidence):
        super().__init__(store, source)
        self.responses = {entry["source_url"]: entry for entry in evidence}
        self.mhra_search_key = "offline-placeholder"

    def get(self, url, params=None, **kwargs):
        public_url = url + ("?" + urlencode(params) if params else "")
        entry = self.responses[public_url]
        self.evidence.append(entry)
        return self.store.get(entry["key"]).body


def run(uk_sample, japan_sample, output, replay=False):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    store = LocalStore(output / "evidence")
    def client(source, filename):
        if replay:
            previous = json.loads((output / filename).read_text())
            return ReplayClient(store, source, [e for row in previous for e in row["evidence"]])
        return EvidenceClient(store, source)
    uk_client = client("uk_mhra", "uk-results.json")
    jp_client = client("japan_pmda", "japan-results.json")
    uk_rows, uk_unique = samples(uk_sample)
    uk = []
    for sample in uk_unique:
        payload = sample["payload"]
        start = len(uk_client.evidence)
        data = payload["data"]
        if data["category"] == "orphan":
            result = enrich(uk_client, data["record"].get("Designation number", ""))
        else:
            result = {"status": "source_named_applicant", "companyRelationships": [
                {"name": name, "role": "listed_ilap_company"} for name in payload["company_names"]]}
        uk.append({"provider_id": sample["provider_id"], "title": payload["title"],
                   "source_url": sample["source_url"], "enrichment": result,
                   "evidence": uk_client.evidence[start:]})
        print(payload["title"], result["status"], [r["name"] for r in result["companyRelationships"]], flush=True)
    parsed = parse_pdf(jp_client.get(SOURCE_URL))
    by_id = {"sakigake:" + row["designationDate"] + ":" + row["listNumber"]: row for row in parsed}
    jp_rows, jp_unique = samples(japan_sample)
    japan = [{"provider_id": sample["provider_id"], "enrichment": by_id[sample["provider_id"]],
              "evidence": jp_client.evidence} for sample in jp_unique]
    summary = {"uk": {"sample_observations": len(uk_rows), "distinct_records": len(uk_unique),
                       "statuses": dict(Counter(r["enrichment"]["status"] for r in uk))},
               "japan": {"sample_observations": len(jp_rows), "distinct_records": len(jp_unique),
                         "applicants_extracted": sum(bool(r["enrichment"]["applicantName"]) for r in japan),
                         "applicant_names_requiring_review": sum(r["enrichment"]["applicantNameReviewRequired"] for r in japan),
                         "approval_dates_extracted": sum(bool(r["enrichment"]["approvalDate"]) for r in japan),
                         "cancelled_designations": sum(r["enrichment"]["designationStatus"] == "cancelled" for r in japan),
                         "full_document_records": len(parsed)},
               "scope": "Source legal names and regulatory roles, not resolved internal company IDs. Cross-country links require separate evidence. No historical event dates inferred from retrieval dates."}
    for name, value in (("uk-results.json", uk), ("japan-results.json", japan), ("summary.json", summary)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    write_review_csv(output, uk, japan)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uk-sample", required=True)
    parser.add_argument("--japan-sample", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--replay", action="store_true", help="Use the prior run's saved evidence, without network access")
    args = parser.parse_args()
    run(args.uk_sample, args.japan_sample, args.output, args.replay)
