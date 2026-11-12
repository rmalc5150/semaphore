# Japan PMDA — November 10, 2026

The existing SAKIGAKE designation feed is repaired and reviewed. **All-drug capture is not complete or currently configured through a bulk account.** Owner confirmed that no PMDA Medi-Navi/My Drug List account exists.

## Owner action: all-drug package-insert access

1. Open [PMDA Medi-Navi](https://www.pmda.go.jp/safety/info-services/medi-navi/0006.html) and register. Browser translation may help with the Japanese instructions. Complete the confirmation email.
2. Register the [My Drug List service](https://push.info.pmda.go.jp/mypage/view/mypage/agreementForUse.html) linked from [PMDA's official service instructions](https://www.pmda.go.jp/safety/info-services/medi-navi/0012.html).
3. After login, open the package-insert bulk-download function (`添付文書一括ダウンロード`), review/accept its terms and choose **all package inserts** (`すべての添付文書`), with PDF and XML/SGML where offered. Do not select only a personally chosen product subset.
4. Tell us when account/export access is available. Do not paste a password or session token. An original official export can also provide the initial import input without sharing a login.

PMDA's [official bulk-download notice](https://www.pmda.go.jp/files/000240672.pdf) and [usage guide](https://www.pmda.go.jp/files/000234826.pdf) document this service. This concerns prescription-drug package inserts, not a proven complete OTC/veterinary corpus or historical versions.

No PMDA-related secret was found in the accessible AWS secret-name inventory. The public search form is available, but requires search conditions; an exhaustive public bulk route was not verified. A diagnostic form probe stopped locally because the optional HTML parser was unavailable; no blank search submission or account bypass was performed. No claim is made that individual public medicine searches require login.

**Remaining engineering after access:** validate actual export/login delivery, ingest unchanged archives and per-drug XML/SGML/PDF artifacts with provider provenance, reconcile product/file counts, schedule repeat/update imports, validate original drug identifiers, then publish and verify all-drug Athena tables. No bulk importer/daily bulk login has been certified by this designation-feed repair.

## Root causes and repairs completed

The old metadata contract had an empty provider-host allowlist, rejecting saved original PDFs. Some older rows also used flattened PDF text that does not match the corrected ruled-table extraction. Those are extraction defects, not missing drugs or permission failures.

Added source contract 2.0.3, `metadata_engine/pmda.py` and shared `pmda_tables.py`. The designation collector and validator now use the same ruled-table parser. Validation checks official origin, SHA-256, PDF integrity, unique date/number identity and exact typed row values. Applicant and marketing-authorisation-holder columns remain distinct. Legacy flattened records cannot be silently promoted to holder assertions. Layout changes fail explicitly rather than producing guessed roles.

Requeued **34 unfinished old-contract jobs** and enabled reviewed-source date queues. Two incompatible legacy jobs were then superseded after verifying the fresh typed capture uses the **identical original provider PDF SHA-256** and covers **every original record ID**. This replaces bad extraction with validated table data; it is not a data-gap exception or deletion. Before/after evidence is in `legacy-replacement-before.json` and `legacy-replacement.json`. No date-failure flags needed resolving in that update.

Original raw objects and failed reports remain. Normal processing continues; a source-lease collision caused one diagnostic replay to exit 2 without processing its queued job. A subsequent replay succeeded. Only the transient diagnostic flag was reset after successful replay/publication; source leases were respected.

## Current capture and Athena proof

Installed **`optima-pmda-designations-daily.timer`**, daily **07:45 Europe/Madrid**, persistent plus boot catch-up, 384 MiB memory and 20% CPU. It captures the full current SAKIGAKE list and validates unique row counts. This is a narrow designation feed, not all PMDA medicines. Existing historical designation-date scopes remain separate and do not establish historical snapshots.

Fresh capture committed **all 25 current designation rows** and verified the complete curated window:

- Manifest: `manifests/collection_runs/source=japan_pmda/dataset=research_records/run_d9a97c7b-a8f5-4237-a8fc-d3a6befde286/final.json`.
- Metadata aggregate **`e617fd63-1cc5-4c57-ab9c-39b509376863`**: **50 raw-complete observations / two raw batches**, including November 10 ingestion. These are repeated observations, not 50 unique drugs.
- Fresh metadata field check **`47b7eb0a-54b3-4a79-b26a-1fba83dbfefb`** and curated field check **`72bef4c6-b15c-4895-896d-3f5e0fff8362`** returned product/applicant data from today's batch. Curated payloads retain separate holder fields and source relationships; legal entity identities are not automatically verified.
- Complete curated release verified: `e42d3ce8adc3f208ac8458d15c54ea45dc0ecba1ede51a7c9142019dc01e1ecc`, receipt in `fresh-publication.json`.

Use **us-east-1 / AwsDataCatalog / optima-collected-data**, result reuse off:

```sql
SELECT source_key, count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations"
WHERE source_key = 'japan_pmda'
GROUP BY source_key;
```

Inspect today's corrected table rows and every saved column:

```sql
SELECT *
FROM optima_regulatory_pilot.research_records_windows
WHERE source = 'japan_pmda'
  AND window_id = 'c3ef3a8f218b54c23da969d249c9f3599d2e766ad9f8de7e810ea2e5acba406d'
ORDER BY rand()
LIMIT 20;
```

The IDE-selected `canada_noc` query concerns a different source. Use entry 21 for PMDA.

## Tests and runtime

**39 focused tests passed**: original PDF/identity/row validation, holder/applicant separation, rejection of corrupted/mismatched/unsupported evidence, canonical PDF parser fixtures and metadata runtime regressions. Edited Python modules compile.

All 15 standard workers and metadata/capture/publication timers were checked online. Metadata source is enabled with zero consecutive failures; other source holds and owner pauses remain separate. The unrelated code-backup service remains failed. The previously observed gap-audit monitor was running another attempt at final inspection; that does not by itself certify its earlier memory issue resolved.

Deployment initially encountered a missing source-package directory; the installer was corrected to create parent directories before installing the shared parser. The subsequent real capture completed successfully. Systemd units are persisted under `systemd/`.

Current feed has no owner key requirement. **All-drug bulk access remains the owner's registration task**, followed by the engineering import/integration checks above. No all-medicine completeness claim is implied by checking the existing feed as reviewed.
