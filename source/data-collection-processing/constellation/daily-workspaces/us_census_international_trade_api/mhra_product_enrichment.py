"""Evidence-backed MHRA holder enrichment. Search results alone never verify a holder."""
import io
import re
from urllib.parse import urljoin, urlsplit

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from regulatory_collection import SourceIssue, require

SEARCH_PAGE = "https://products.mhra.gov.uk/search"
INDEX = "https://mhraproducts4853.search.windows.net/indexes/products-index/docs"
REVISION = "mhra-exact-licence-spc-v1"


def licence_numbers(value):
    """Expand explicit, bounded ranges; never guess a missing licence number."""
    result = []
    pattern = r"\b(PLGB|PLNI|PL)[\s/]*(\d{5})\s*/\s*(\d{4})(?:\s*-\s*(\d{4}))?"
    for prefix, holder, first, last in re.findall(pattern, value or "", re.I):
        end = int(last or first)
        if not int(first) <= end <= int(first) + 20:
            raise SourceIssue("mhra_licence_range_invalid")
        result.extend(f"{prefix.upper()}{holder}{number:04d}" for number in range(int(first), end + 1))
    return list(dict.fromkeys(result))


def numeric_licence(value):
    return re.sub(r"^PL(?:GB|NI)?", "", re.sub(r"[^A-Z0-9]", "", value.upper()))


def public_search_key(client):
    if hasattr(client, "mhra_search_key"):
        return client.mhra_search_key
    if getattr(client, "mhra_search_failure", None):
        raise SourceIssue(client.mhra_search_failure)
    try:
        return discover_public_search_key(client)
    except SourceIssue as exc:
        client.mhra_search_failure = exc.code
        raise


def discover_public_search_key(client):
    html = client.get(SEARCH_PAGE, persist=False).decode("utf-8")
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
    # Discover the public website's read-only query key; do not hardcode it or
    # put it in evidence URLs. A changed client layout leaves records unresolved.
    for src in scripts[:20]:
        url = urljoin(SEARCH_PAGE, src)
        if urlsplit(url).hostname != "products.mhra.gov.uk":
            continue
        script = client.get(url, persist=False).decode("utf-8")
        if "mhraproducts4853" not in script:
            continue
        match = re.search(r'append\("api-key","([^"]+)"\)', script)
        if match:
            client.mhra_search_key = match.group(1)
            return client.mhra_search_key
    raise SourceIssue("mhra_public_search_configuration_changed")


def spc_holder(raw, requested_licence):
    require(raw.lstrip().startswith(b"%PDF"), "mhra_product_document_not_pdf")
    try:
        text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(raw)).pages)
    except PdfReadError as exc:
        raise SourceIssue("mhra_product_pdf_unreadable") from exc
    sections = re.search(
        r"(?:^|\n)\s*7\.?\s+MARKETING AUTHORISATION HOLDER\s*\n(.*?)"
        r"(?:^|\n)\s*8\.?\s+MARKETING AUTHORISATION NUMBER(?:\s*\(S\)|S)?\s*\n(.*?)"
        r"(?:^|\n)\s*9\.?\s+DATE", text, re.S | re.I)
    if not sections:
        return None
    licences = licence_numbers(sections.group(2))
    if numeric_licence(requested_licence) not in {numeric_licence(x) for x in licences}:
        return None
    lines = [line.strip() for line in sections.group(1).splitlines() if line.strip()]
    if not lines:
        return None
    # Require a complete legal name before any address. Wrapped or unfamiliar
    # names stay unresolved rather than returning a truncated organisation.
    name = lines[0].rstrip(",;")
    if not re.search(r"\b(?:Limited|Ltd\.?|plc|GmbH|B\.V\.|S\.A\.|AB|AG|LLC|EEIG|Inc\.?)$", name, re.I):
        return None
    return {"name": name, "role": "marketing_authorisation_holder", "jurisdiction": "UK",
            "licenceNumber": requested_licence, "documentLicenceNumbers": licences,
            "matchBasis": "licence_in_search_metadata_and_spc_section_8",
            "temporalBasis": "retrieved_product_information_not_historical_holder_or_current_authorisation_status",
            "holderSectionText": sections.group(1).strip()}


def enrich(client, designation):
    licences = licence_numbers(designation)
    result = {"revision": REVISION, "licenceNumbers": licences, "companyRelationships": [],
              "unresolvedLicenceNumbers": [], "status": "unresolved"}
    if not licences:
        result["reason"] = "licence_number_unparsed"
        return result
    key = public_search_key(client)
    for licence in licences:
        variants = [licence] if licence.startswith("PLNI") else [prefix + numeric_licence(licence) for prefix in ("PL", "PLGB")]
        licence_filter = " or ".join("p eq '" + value + "'" for value in variants)
        response = client.json(INDEX, params={"api-version": "2017-11-11",
            "search": "*", "$top": 100, "$count": "true",
            "$filter": "doc_type eq 'Spc' and pl_number/any(p: " + licence_filter + ")"},
            api_key=key, api_key_parameter="api-key")
        documents = response.get("value", [])
        require(isinstance(documents, list), "mhra_search_shape_changed")
        require(response.get("@odata.count", len(documents)) <= 100, "mhra_search_truncated")
        matches = []
        for document in documents:
            if numeric_licence(licence) not in {numeric_licence(x) for x in document.get("pl_number", [])}:
                continue
            url = document.get("metadata_storage_path", "")
            if urlsplit(url).scheme != "https" or urlsplit(url).hostname != "mhraproducts4853.blob.core.windows.net":
                continue
            relationship = spc_holder(client.get(url), licence)
            if relationship:
                matches.append({**relationship, "sourceUrl": url, "productName": document.get("product_name"),
                                "activeSubstances": document.get("substance_name", [])})
        if matches and len({m["name"].casefold() for m in matches}) == 1:
            result["companyRelationships"].append(matches[0])
        else:
            result["unresolvedLicenceNumbers"].append(licence)
    if result["companyRelationships"]:
        result["status"] = "partial" if result["unresolvedLicenceNumbers"] else "verified_source_relationship"
    return result
