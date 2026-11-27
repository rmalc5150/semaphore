# Decodo proxy verification — 18 November 2026

**Completed later November 18:** the replacement password was verified and the owner-approved PDF fallback is enabled with a shared four-attempt daily cap. No password action remains. [Current configuration and evidence](../2026-11-18-pdf-fallback/README.md).

**Result: the configured HTTPS proxy can download original PDF bytes successfully on both the controller and the production worker.** All four downloads matched known direct-original SHA-256 hashes and passed strict PDF parsing. This uses a standard proxy connection, not the JSON scraping API. No base64 output or additional subscription was needed for these tests.

| Document | Controller | Worker | Validation |
| --- | --- | --- | --- |
| W3C control PDF | HTTP 200; 13,264 bytes | HTTP 200; same bytes | Original checksum match; one page |
| medRxiv sample | HTTP 200; 781,135 bytes | HTTP 200; same bytes | Original checksum match; 49 pages; expected DOI present |

Endpoint: `https://gate.decodo.com:10001`. TLS verification remained enabled. Four bounded proxy requests were made in total; no scraping API requests, account purchases, plan changes or automatic collector activation were made in this step. The worker wrote diagnostic evidence only to its local test directory.

[Validated proxy-downloaded medRxiv PDF](medrxiv-proxy.pdf).

## Configuration correction and required password rotation

The endpoint field originally contained the provider's `host:port:username:password` export. It has been normalised to the HTTPS endpoint above, with authentication retained only in `decodo-proxy-username` and `decodo-proxy-password`. All other secret fields were preserved; Secrets Manager retains the preceding version. See `endpoint-normalization.json` for non-secret version metadata.

**The initial diagnostic attempted to parse the combined value as a URL port and accidentally exposed the proxy login in its exception output.** Subsequent scripts suppress credential-bearing exception text and log only safe error types/status codes. No login value is included in these report files. The owner should regenerate this proxy password in Decodo, then update only `decodo-proxy-password` in the existing `proxies` secret. Do not reinsert login details into the endpoint field or paste the new password into chat.

Automatic proxy collection remains disabled pending password rotation and a short recheck. This successful download test does not by itself establish collector fallback integration, metadata processing, complete preprint coverage or Athena publication. The old JSON scraping PDF route remains disabled.

## Evidence

- `results.json`: controller download statuses, hashes and strict validation.
- `worker-proxy-result.json`: same checks from the production worker.
- `endpoint-normalization.json`: safe endpoint correction/version receipt; no login values.
- `probe.py` and `worker_probe.py`: bounded reproductions; they read credentials from Secrets Manager at runtime.
- `control-proxy.pdf` and `medrxiv-proxy.pdf`: diagnostic native PDF downloads outside the production collection bucket.
