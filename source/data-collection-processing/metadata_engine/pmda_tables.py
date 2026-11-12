"""Canonical ruled-table extraction from the official PMDA SAKIGAKE PDF."""
import io,re
from datetime import date

def japanese_date(value: str) -> date:
    era, year, month, day = re.fullmatch(r"([HRS])(\d+)\.(\d+)\.(\d+)", value).groups()
    base = {"H": 1988, "R": 2018, "S": 1925}[era]
    return date(base + int(year), int(month), int(day))


def parse_pdf(raw: bytes) -> list[dict]:
    import pdfplumber

    # Read ruled cells, not flattened page text: applicant and holder are
    # different columns, and headers/footnotes must never enter a record.
    records = []
    seen = set()
    fields = ("designationRound", "listNumber", "designationDateNative", "designatedProductName",
              "applicantName", "designatedIndication", "approvalDateNative", "approvedProductName",
              "activeSubstance", "marketingAuthorisationHolder", "approvedIndication", "remarks")
    def clean_cell(value):
        # Join typographic line wraps without destroying spaces inside Latin names.
        text = re.sub(r"(?<=[A-Za-z])\n(?=[A-Za-z])", " ", value or "")
        return re.sub(r"\s+", " ", text.replace("\n", "")).strip()

    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            if len(tables) != 1:
                raise RuntimeError("PMDA table layout changed: expected one table per page")
            table = tables[0]
            header = [clean_cell(cell) for cell in table[0]]
            if len(header) != 12 or header[2] != "指定日" or header[4] != "指定を受けた申請者" or header[9] != "製造販売承認を受けた者":
                raise RuntimeError("PMDA table headers changed")
            for cells in table[1:]:
                if len(cells) != 12:
                    raise RuntimeError("PMDA table row width changed")
                row = dict(zip(fields, map(clean_cell, cells)))
                # The round column spans rows/pages; date + number is the
                # existing stable identity. Do not attribute a merged round cell.
                row.pop("designationRound")
                if not row["listNumber"].isdigit() or not row["applicantName"] or not row["designatedProductName"]:
                    raise RuntimeError("PMDA table identity/applicant missing")
                row["designationDate"] = japanese_date(row["designationDateNative"]).isoformat()
                identity = (row["designationDate"], row["listNumber"])
                if identity in seen:
                    raise RuntimeError("duplicate PMDA designation identity")
                seen.add(identity)
                approval = re.search(r"[HRS]\d+\.\d+\.\d+", row["approvalDateNative"])
                row["approvalDate"] = japanese_date(approval.group()).isoformat() if approval else None
                for field in ("approvedProductName", "activeSubstance", "marketingAuthorisationHolder", "approvedIndication"):
                    if row[field] in ("", "－", "—", "-"):
                        row[field] = None
                cancelled = re.search(r"指定取消\s*[（(]([HRS]\d+\.\d+\.\d+)[）)]", row["remarks"])
                row["designationStatus"] = "cancelled" if "指定取消" in row["remarks"] else "listed"
                row["cancellationDate"] = japanese_date(cancelled.group(1)).isoformat() if cancelled else None
                row["sourcePage"] = page_number
                row["applicantNameReviewRequired"] = "株式会" in row["applicantName"] and "株式会社" not in row["applicantName"]
                row["companyRelationships"] = [{"name": row["applicantName"], "role": "listed_designation_applicant",
                                                "nameReviewRequired": row["applicantNameReviewRequired"]}]
                if row["marketingAuthorisationHolder"]:
                    row["companyRelationships"].append({"name": row["marketingAuthorisationHolder"], "role": "marketing_authorisation_holder"})
                row["recordText"] = " ".join(clean_cell(cell) for cell in cells[3:])
                records.append(row)
    if not records:
        raise RuntimeError("no SAKIGAKE records could be parsed from PMDA PDF")
    return records

