# Credential-backed collection rollout — 27 October 2026

Daily capture runs on the t3 controller. Historical capture runs through the existing m7i.large worker pool with its existing 2 CPU / 6 GiB shared limits. All configured historical scopes start in 2016. These are initial, explicit collection scopes; enabling a route does not certify complete source coverage or Athena publication.

The existing daily API timer now includes FRED and OpenDART as well as the new credential adapters. Historical dispatch includes all selected sources. EPO remains enabled and subject to its existing shared request/byte budgets.

| Source | Initial capture scope |
| --- | --- |
| Comtrade | Keyed imports/exports for the existing five reporters, four battery/mineral HS6 codes and world partner totals; annual partitions. |
| FRED / ALFRED | Existing 22-series selection, observation years since 2016 and bounded realtime intervals. Three-year vintage intervals avoid FRED's 2,000-vintage-date JSON limit. |
| Ember | Monthly generation and demand for all returned geographies; Ember attribution retained. |
| WTO Timeseries | All 55 currently catalogued indicators, all reporting economies, provider default product/partner scopes; annual partitions with reconciled totals and offset pagination. Indicators with no time dimension are captured once as current snapshots with no invented historical event date. |
| WTO Quantitative Restrictions | Notifications submitted since 2016 and restrictions entering into force since 2016, with page totals checked. Older restrictions still in force are outside this initial scope. |
| WTO ePing | English SPS/TBT notification metadata for all notifying members, partitioned by distribution date; document attachments are outside this scope. |
| Copernicus | ERA5/ERA5-Land hourly temperature and precipitation at eight regional reference cells. Raw NetCDF artifacts and checksums; weather-value extraction remains separate. Downloads require dataset licences. |
| Census | Monthly imports/exports for TOTAL and the four existing battery/mineral HS6 codes, by partner country. |
| USDA FAS | Current PSD data for corn, wheat, rice, soybeans and cotton, all countries and market years since 2016. Historical forecast vintages are not supplied by this route. |
| EPO | Existing applicant discovery and rotating legal-event refresh; unchanged budgets. |

Copernicus authenticated successfully but returned HTTP 403, `required licences not accepted`, for an actual ERA5 download submission. Accept the terms for both datasets using the same CDS account as the stored token:

- https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=download#manage-licences
- https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=download#manage-licences

USDA returned HTTP 500 for correctly configured requests using its documented `API_KEY` header. Census initially timed out and also returned a redirect. These attempts are retained as failures, not empty or completed data. Their source retries use backoff. Licence acceptance or corrected credentials may require clearing the relevant source hold to retry immediately; do not discard failure receipts.

`current-status.json` records native scheduler counts, timestamps and sample manifests. Counts are task-level record occurrences, not necessarily distinct records. `verify.py` is a manual JSON evidence check; it does not update the user's static data-source-status Markdown file.

Deployment artifacts and SSM command IDs are in `deployment.json`; no credential values are written to these files. Source credentials stay in the existing Secrets Manager secret. Signed Copernicus download queries are not saved in evidence. No IAM permissions, instance size or collection resource limits were expanded.

Automatic shutdown has been rearmed for the expanded collection scope. Unresolved provider failures go to the existing daily repair update and do not prevent shutdown once healthy work is finished. Healthy backlog, pagination and provider quota waits remain unfinished work.

Comtrade keyed requests share a conservative 400-request UTC-day allowance across both hosts. Exhaustion defers unfinished work rather than treating it as a source failure. Final validation: 62 targeted tests passed.
