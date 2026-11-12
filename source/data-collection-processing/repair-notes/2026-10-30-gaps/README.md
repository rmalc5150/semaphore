# October 30 — unavailable data versus repairable failures

## Established unavailable data

medRxiv was launched in June 2019, according to the provider:
https://www.cshl.edu/cshl-and-plos-partner-to-host-papers-on-medrxiv/

`reviewed_source_gaps.py` records a narrowly scoped decision for medRxiv only, for windows wholly inside `[2016-01-01, 2019-06-01)`. June remains eligible. bioRxiv is not excluded. The decision is matched by source, adapter, repository and dates; dates overridden in query parameters are not eligible.

The collector writes a durable `accepted_unavailable` decision receipt without making a provider request. Scheduler completion and unavailable counts stay separate; unavailable scopes are not sent to the analytical publication queue as fabricated empty datasets. Later scheduler passes skip accepted scopes. The gap reporter also applies this reviewed decision to retained failure receipts, so old pre-launch failures no longer create recurring repair alerts.

Live gap refresh succeeded at 11:07 UTC (12:07 Madrid), October 30: **41 accepted-unavailable windows**, **139 flagged merged gap intervals**, **51 record-only intervals**. These are intervals, not numbers of failed sources. See `refresh-summary.json`. This does not establish that all other intervals are genuine missing data.

## Repairs and live verification

- WTO: opt-in HTTP 204 handling saves the empty response evidence and completes an initial empty query. Empty responses during active pagination still fail. Live 2016 ITS_CS_AM5 replay committed a complete zero-record manifest (`wto-replays.json`). This is not a permanent unavailability exclusion or an Athena verification claim. The scheduler must reconcile the replay before all old WTO alerts disappear.
- Census: live stored-key request redirects to `/data/invalid_key.html`. Updated the adapter to identify this as `census_api_key_rejected`; no secret values or authenticated redirect URL were logged. Owner must confirm activation or update the `US-census` secret field, then retry. This is not a historical data gap.
- Gap reporting: the full database-history read timed out; replaced it with 500-job keyset batches. The refreshed report was successfully written to the existing monitoring location. The earlier failed attempt is retained in session evidence; no historical failures were deleted.

## Deployment and tests

Deployment succeeded: 718 remote module copies and 64 local daily-workspace copies. New collector invocations load the updates; no worker/service pause was required. `source-deployment-result.json` records success.

47 relevant tests passed. Tests verify the exclusion boundary/repository, durable unavailable receipts without HTTP calls or false completion, retained bioRxiv alerts, opt-in 204 handling, and pagination rejection. See `tests.log`.

Watchdog refresh uses `notifications=False`: no test SMS or email. Existing owner source pauses remain unchanged.

## Not excluded

- FDA undated submissions: unavailable field values may be retained as unknown, but that does not justify excluding entire applications or months. Earlier parser fixes still need scoped replay/reconciliation for old failures.
- USGS 404 / TED AccessDenied: establish retrieval/permission failures, not nonexistence of the underlying files.
- FRED, ERA5, USDA, OpenDART and other WTO failures: require response/entitlement/request investigation.
- Zenodo, DataCite, post-launch preprints, EMA, Europe PMC and USAspending: parsing, pagination, limits or transient requests remain repair work.

The refreshed [source status file](../../../data-source-status-2026-10-26.md) puts confirmed owner actions and unresolved high-priority repairs first. All 158 catalog entries and SQL blocks are preserved; older counts remain explicitly dated.
