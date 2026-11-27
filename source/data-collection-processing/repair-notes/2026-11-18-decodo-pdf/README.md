# Decodo PDF download test — 18 November 2026

**Later November 18 update:** proxy credentials were supplied and the HTTPS proxy passed both PDF tests on controller and worker. The endpoint was normalised; a password rotation is required after an initial diagnostic exposed the login. [Current results and next step](../2026-11-18-decodo-proxy/README.md).

**Result:** the tested Decodo Web Data API transport still does not return a usable original PDF. The previously blocked medRxiv PDF now downloads directly, including through the production downloader on the worker. No production configuration was changed and no diagnostic PDF was published to Athena.

| Test | Result |
| --- | --- |
| Direct W3C control PDF | HTTP 200; 13,264 bytes; strict PDF validation passed |
| Decodo control PDF, `Accept: application/pdf` | HTTP 200 but JSON response; reconstructed UTF-8 bytes failed strict PDF validation and differed from the known original; Latin-1/Windows-1252 encoding was impossible |
| Direct medRxiv PDF | HTTP 200; 781,135 bytes; 49 pages; strict validation and expected DOI passed |
| Decodo medRxiv PDF, `Accept: application/pdf` | HTTP 200 but JSON response; all three tested reconstruction methods failed |
| Worker production `EvidenceClient.get` | Same 781,135-byte valid medRxiv PDF and checksum as controller direct download |
| Worker `requests.get` | Same valid PDF and checksum |
| Decodo standard proxy / Site Unblocker | Not tested: Secrets Manager contains only `decodo-web` and `decodo-web-scraping`, with no separate proxy login configured. No inference about account entitlement is made |

The two Decodo calls used the configured Bearer key and normal shared request reservation, within the existing 24-request diagnostic allowance. API task IDs: `7528736989705669633` (control) and `7528737029245423617` (medRxiv). Their HTTP 200 statuses do not establish successful PDF transport. The key is not the identified problem.

## Working download

[Validated medRxiv PDF](medrxiv-direct.pdf):

- URL: `https://www.medrxiv.org/content/10.64898/2026.05.07.26352693v2.full.pdf`
- SHA-256: `2711c86f4189824a8324c0ecafdc2a807485054560bb7d50cef2eee9b7f821ef`
- Native PDF bytes saved directly; no JSON reconstruction or PDF repair.
- This is a successful test of one preprint, not assurance that every PDF or future request will succeed.

The existing direct download route works for this document. Keep the failed Decodo PDF fallback disabled. Other source failures must retain their own errors and checkpoints; do not treat this sample as full source history, metadata processing or Athena publication verification.

## If a proxy fallback is needed

Decodo documents standard [residential proxy connections](https://help.decodo.com/docs/residential-proxy-quick-start) and [Site Unblocker](https://help.decodo.com/docs/site-unblocker-quick-start). These use proxy username/password authentication, rather than the Web Data API Bearer token. Confirm existing account access before selecting either. Proxy transport has not been validated for this target; no new subscription, credentials or paid trial was created.

If the existing plan includes a suitable proxy, save its endpoint, username and password in Secrets Manager and provide the secret ARN/field names. Do not paste credentials in chat. The next test should compare a proxy-downloaded control against its direct checksum, then validate the blocked document. Do not enable automatic collection until that test passes.

## Evidence

- `results.json`: two direct/API comparisons, response types, sizes, parse results and hashes.
- `credential-fields.json`: field names only; no credential values.
- `worker-direct-result.json`: production worker download and matching PDF identity.
- `probe.py`, `worker_direct.py`: bounded reproductions. The two-call API probe should not be repeated as a scheduled job.
- `control-direct.pdf`, `medrxiv-direct.pdf`: original diagnostic downloads, outside production storage.

Worker diagnostic evidence is in a local test directory, not the production collection bucket. Existing HTML scraping and unrelated pipelines were left unchanged.
