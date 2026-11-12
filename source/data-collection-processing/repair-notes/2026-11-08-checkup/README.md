# November 8 checkup

## Completed

- Read the supplied alert and the latest monitoring/representative source receipts. Historical gap evidence includes older October failures; these remain open, not assumed newly failed or permanently unavailable.
- Fixed two sticky recoveries: a clean, fresh daily audit can clear its older process-failure alert; an empty publication queue can clear its old stall only with verified publication receipt evidence for every configured owner and no pending work.
- Deployed collection_alerts.py to the existing watchdog Lambda with revision/checksum verification and package backup. The controller uses the updated collection_health_exporter.py. No manual notifications sent.
- Selected live reevaluation cleared both old incidents. The November 8 09:18 UTC audit records 107 successful checks, 100 shared-table readbacks, 429 S3 objects and no query/S3/receipt-query failures. These checks do not certify full history or specialist payload completeness.
- 44 focused tests passed. See tests.log, monitoring-verification.json and monitoring-deployment.json.

## Database bottleneck repaired after approval

The USDA historical dispatch attempt timed out before it registered a new job. Census dispatch was not reached. The query plan estimates 24,396 rows plus sorting, because backfill_jobs has no source-key index. Subsequent inspection found abandoned controller SELECTs and a source-selection SELECT running for over an hour in the metadata engine.

Initial online index attempts made no change: the controller lacks ALTER privileges; the existing host-matched administrator credential encountered a five-second metadata-lock timeout. No new access grant was needed.

Automatic approval review initially rejected query cancellation because of potential disruption. The owner subsequently explicitly approved the exact database-repair-proposal.md. Six matching abandoned controller queries were canceled; the previously observed metadata query had already ended and was not canceled. The online index was then created in 46.18 seconds; EXPLAIN now selects source_status_updated with a backward index scan. USDA dispatch succeeded in 0.701 seconds and Census in 0.248 seconds. Both exact jobs subsequently executed. USDA captured 1,500 cotton records for 2016; manifest completion, batch checksums and row counts independently verified in usda-s3-verification.json. Census initially failed with HTTP 204, leading to the repair below. Athena publication of these repaired scopes remains unverified. Ten migration tests passed; dispatcher SELECTs now carry a ten-second server time limit.

## Still open

- Historical scopes for FDA, preprints, Census, EDINET, FRED, DataCite, Zenodo, BLS, ClinicalTrials, MHRA, OpenDART, USGS, TED, CTIS, Copernicus, WTO, Europe PMC, USDA and USAspending; see historical-error-summary.json. Repair/replay and artifact validation remain engineering work. HTTP errors alone do not establish permanent gaps.
- Shared-lock waits, HKEX inventory/dependent disclosures, patent office-action catch-up and market mapping gaps. Email baseline: 175 daily/202 historical symbols, 52 reviewed exclusions.
- Latest patent journal showed 50 committed office-action records at 18:41 UTC; this does not prove full window completion or Athena publication of that batch.

## Owner action

Database repair approved; no further approval requested. No new API key or subscription requirement was established. Existing Census/Copernicus activation is not being requested again. Optional: continue the SEC/FDA enforcement/EIA Athena payload checks and return query IDs with any missing fields.

## Census request repair

The failed worker scope used E_COMMODITY=TOTAL. The [official Census trade API guide](https://www.census.gov/foreign-trade/reference/guides/Guide_to_International_Trade_Datasets.pdf), default-parameter section, defines a dash as the total code. The adapter now maps only the configured TOTAL label to '-', preserving saved job identity, original returned payload and specific HS codes. It does not treat arbitrary HTTP failures as empty success.

The corrected exact May 2017 exports adapter probe returned 254 rows, 254 unique identities and no next cursor. See census-adapter-live.json. Twenty-one credential tests passed. Deployment to daily workspaces and 149 historical module files succeeded; see census-deployment-result.json. The original comparison probe timed out on the no-filter variant after recording two HTTP 204 responses; it did not establish success. No key was printed. Production commit and Athena publication of the Census fix are still pending.
