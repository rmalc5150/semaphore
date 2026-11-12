"""Bounded retrieval and validation of original SEC complete submissions.

Only SEC archive URLs for the expected accession/issuer are fetched. HTTP
denials, redirects, incomplete SGML and mismatched filings fail closed.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 16 * 1024 * 1024
USER_AGENT = "Optima Holdings metadata-engine/1.1 support@optima-holdings.com"


class DocumentError(ValueError):
    """An explicit missing, invalid or inaccessible evidence result."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_url(url, accession, ciks):
    parsed = urlsplit(url)
    match = re.fullmatch(r"/Archives/edgar/data/([0-9]+)/(?:([0-9]{18})/)?([0-9]{10}-[0-9]{2}-[0-9]{6})\.txt", parsed.path)
    if (parsed.scheme != "https" or parsed.netloc != "www.sec.gov" or parsed.query
            or parsed.fragment or not match or match[3] != accession
            or (match[2] and match[2] != accession.replace("-", ""))
            or int(match[1]) not in {int(cik) for cik in ciks}):
        raise DocumentError("sec_document_url_identity_mismatch")


def validate_submission(body, accession, ciks, form):
    if not body or len(body) > MAX_BYTES:
        raise DocumentError("sec_document_empty_or_oversized")
    lowered = body.lower()
    if any(marker in lowered for marker in (b"request rate threshold exceeded", b"your request originates from an undeclared automated tool", b"<title>access denied")):
        raise DocumentError("sec_document_access_blocked")
    header_end = body.find(b"</SEC-HEADER>")
    if not body.startswith(b"<SEC-DOCUMENT>") or header_end < 0 or not body.rstrip().endswith(b"</SEC-DOCUMENT>"):
        raise DocumentError("sec_submission_incomplete")
    header = body[:header_end].decode("ascii", errors="replace")
    identity = re.search(r"ACCESSION NUMBER:\s*([0-9-]+)", header)
    header_ciks = re.findall(r"CENTRAL INDEX KEY:\s*([0-9]+)", header)
    if identity is None or identity[1] != accession or not ({int(c) for c in header_ciks} & {int(c) for c in ciks}):
        raise DocumentError("sec_document_identity_mismatch")
    form_match = re.search(r"CONFORMED SUBMISSION TYPE:\s*([^\r\n]+)", header)
    if form_match is None or form_match[1].strip() != form:
        raise DocumentError("sec_document_form_mismatch")
    blocks = list(re.finditer(rb"<DOCUMENT>(.*?)</DOCUMENT>", body, re.S))
    if not blocks or len(blocks) != body.count(b"<DOCUMENT>") or len(blocks) != body.count(b"</DOCUMENT>"):
        raise DocumentError("sec_document_blocks_incomplete")
    documents = []
    for block in blocks:
        kind = re.search(rb"<TYPE>([^\r\n<]+)", block[1])
        filename = re.search(rb"<FILENAME>([^\r\n<]+)", block[1])
        content = re.search(rb"<TEXT>(.*?)</TEXT>", block[1], re.S)
        if not kind or not filename or not content or not content[1].strip():
            raise DocumentError("sec_submission_block_incomplete")
        documents.append({"type": kind[1].decode("ascii").strip(), "filename": filename[1].decode("ascii").strip(),
                          "byte_start": block.start(), "byte_end": block.end()})
    if not any(doc["type"] == form for doc in documents):
        raise DocumentError("sec_primary_document_missing")
    return {"accession": accession, "form": form, "documents": documents,
            "completeness_basis": "complete SEC submission with matching header and closed document blocks"}


def retrieve_submission(record, opener=None):
    url = record["source_url"]
    accession = record["source_record_id"]
    ciks = [row["cik"] for row in record["payload"]["issuer_rows"]]
    validate_url(url, accession, ciks)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity", "Accept": "text/plain"})
    try:
        response = (opener or build_opener(NoRedirect())).open(request, timeout=45)
    except HTTPError as error:
        status = error.code
        error.close()
        raise DocumentError("sec_document_http_" + str(status)) from None
    with response:
        if response.status != 200:
            raise DocumentError("sec_document_http_" + str(response.status))
        validate_url(response.geturl(), accession, ciks)
        encoding = response.headers.get("Content-Encoding", "identity")
        if encoding != "identity":
            raise DocumentError("sec_document_unexpected_encoding")
        length = response.headers.get("Content-Length")
        if length is not None and int(length) > MAX_BYTES:
            raise DocumentError("sec_document_oversized")
        body = response.read(MAX_BYTES + 1)
        if length is not None and len(body) != int(length):
            raise DocumentError("sec_document_length_mismatch")
        receipt = {"source_url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(), "http_status": 200,
                   "response_headers": {key: response.headers[key] for key in ("Content-Type", "Content-Length", "Last-Modified", "ETag") if key in response.headers}}
    validation = validate_submission(body, accession, ciks, record["payload"]["form"])
    return body, {**receipt, **validation, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}


def archive_submission(s3, bucket, body, receipt):
    """Store original bytes conditionally, then independently verify read-back."""
    from botocore.exceptions import ClientError
    key = "research-data/constellation-backfill/metadata-engine/source_documents/sec_edgar/" + receipt["sha256"] + ".txt"
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=body, ServerSideEncryption="AES256", ContentType="text/plain", IfNoneMatch="*")
    except ClientError as error:
        if error.response["Error"]["Code"] not in {"PreconditionFailed", "412"}:
            raise
    response = s3.get_object(Bucket=bucket, Key=key)
    try:
        saved = response["Body"].read(MAX_BYTES + 1)
    finally:
        response["Body"].close()
    if saved != body or hashlib.sha256(saved).hexdigest() != receipt["sha256"]:
        raise DocumentError("sec_document_s3_checksum_mismatch")
    return {**receipt, "artifact_kind": "primary_document", "origin": "first_party_source", "s3_uri": "s3://" + bucket + "/" + key,
            "verification": "S3 bytes and SHA-256 verified"}
