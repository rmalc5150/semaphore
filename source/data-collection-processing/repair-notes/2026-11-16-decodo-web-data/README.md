# Decodo Web Data API PDF fallback — unsupported transport; route retired


**November 18 retest:** requesting `Accept: application/pdf` still returned invalid PDF text through the API, including for a known control. The same medRxiv sample now downloads directly and passes strict PDF and DOI validation on both controller and worker. [Current results and validated file](../2026-11-18-decodo-pdf/README.md). This does not enable the Decodo fallback or certify all preprints.

**Owner credential configured:** Secrets Manager ARN `arn:aws:secretsmanager:us-east-1:059416028963:secret:proxies-fkWzVV`, JSON key `decodo-web`. Both the controller and production worker can read it. The new Bearer token authenticates successfully. No new credential or IAM permission is currently needed. Existing Basic-auth fields remain available for the old HTML scrapers.

**Live result:** two bounded requests to `https://data.decodo.com/v1/scrape`, using support's exact PDF example and `{ "url": "…" }`, returned HTTP 200 and target HTTP 200. They did **not** return the promised base64 PDF. The response is nested under `results[0]`, has `type: "raw"`, and `content` begins `%PDF-`.

The saved response fails strict base64 validation. UTF-8 reconstruction fails strict PDF parsing with `Broken xref table`; Windows-1252 and Latin-1 reconstruction fail because the string contains characters outside those encodings. None of these attempts produced a verified original PDF. The returned HTTP content length is not used to infer corruption because compression could change it.

**Production state:** fallback remains disabled in `config/decodo-web-data.json` and has not been deployed to worker collectors. No PDF from this test was promoted to a committed collection manifest or Athena. The existing HTML routes and unrelated collectors were not changed. A guard prevents the unverified route from making production paid requests; only the explicit diagnostic pilot can bypass that guard.

**Testing:** **85 focused tests passed**, including exact secret-field selection, actual nested-response support, rejection of raw PDF strings, malformed/base64/identity checks, bounded request handling, disabled-route protection and cursor continuity after a successful paid fallback.

## Support outcome and next steps

The owner reports that Decodo support confirmed **base64 output is not offered**. The earlier support request is closed; do not ask for base64 again or repeat paid PDF probes against this route. The original draft is retained in `support-follow-up.superseded.txt` as historical evidence.

The requirement is to preserve the original PDF bytes, not to use base64 specifically. The tested JSON response does not meet that requirement. Existing HTML collection remains separate and is unaffected.

Next engineering work: use direct original downloads or an authorised provider archive/mirror where available. A standard proxy connection is another candidate because it transports the HTTP response rather than serialising it into a JSON text field. Decodo documents [residential proxy access](https://help.decodo.com/docs/residential-proxy-quick-start) and [HTTP/HTTPS/SOCKS5 protocols](https://help.decodo.com/docs/residential-proxy-protocols). This does **not** establish that the current subscription includes proxy access or that a proxy will retrieve the blocked medRxiv PDF. Verify entitlement and credentials before any bounded test; validate original PDF bytes, DOI, metadata and publication before activation. No new subscription or paid trial has been requested or started.

## Experimental implementation retained, disabled

- Direct preprint retrieval remains first; only a publisher HTTP 403 selects this fallback. A publisher 429 does not trigger extra paid requests.
- Bearer authentication uses only the configured Web Data API key, never old Basic-auth fields.
- Response decoding supports a top-level `content` field or a single `results[0]` envelope, with explicit provider status validation.
- A valid base64 response must decode to a bounded, complete PDF that passes strict parsing and contains the expected DOI. Invalid strings remain diagnostic evidence.
- Gateway evidence is archived separately with the Bearer value redacted. Only validated original PDF bytes can become provider PDF evidence.
- One successful paid fallback is committed per page, advancing the cursor only over consumed provider rows. Initial shared allowance: **24 requests per UTC day**, adjustable after plan usage is verified. Source-specific failures and quota pauses do not stop unrelated sources.

Do not rerun `pilot.py` against the unsupported base64 route. A different transport requires its own bounded download test, strict PDF and identity validation, runtime backups/import checks, metadata processing and a precisely scoped Athena verification. A successful download alone does not prove complete history or a complete pipeline.

## Evidence

- `live-validation.json`: target status, task ID, exact request, redacted envelope reference and explicit non-publication status.
- `encoding-inspection.json`: live payload was not base64.
- `raw-pdf-validation.json`: failures of the three standard reconstruction attempts.
- `worker-secret-access-result.json`: successful worker read; no credential value printed.
- `tests-configured.log`: 85 passing tests.
- Diagnostic response: `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/biorxiv_medrxiv_preprints/134a38a95b5011768e2bd7ec455933c95e0bc06717f92df6de03c948b13e5125`. This is a JSON transport response, **not** a validated original PDF.

The vendor's [synchronous-response example](https://help.decodo.com/docs/web-data-api-scrape-real-time-requests) also uses `results[0].content`. The checked [parameter reference](https://help.decodo.com/docs/web-data-api-scrape-parameters) does not identify the PDF base64 output option needed to resolve this test.

EDINET historical year 2016 remains excluded by the owner's separate decision; this change does not alter it.
