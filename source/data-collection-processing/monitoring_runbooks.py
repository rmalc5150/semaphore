"""Repair guidance included directly in the daily email."""
GUIDES={
 'source_http_400': [
  'Open the named service journal: journalctl -u <service> --since "24 hours ago" --no-pager. Identify source, date window, reason and manifest; inspect the saved request/response evidence without exposing credentials.',
  'For ClinicalTrials.gov history, inspect ClinicalTrials.page in regulatory_sources.py and config/core-historical-schedule.json. Compare the failed February 2021 query.term, LastUpdatePostDate sort, date bounds and pageToken with the saved response. Correct the rejected parameter; keep the original manifest and checkpoint. Run .venv-athena/bin/python -m unittest test_regulatory_collection after the change.',
  'Replay one affected window with the existing runner after its scheduled invocation has finished. Keep the same task identity and approved provider limits.',
  'Require a completed/exhausted manifest, verified S3 batches and a successful source-filtered Athena readback before marking that exact window recovered.'],
 'eia_html_instead_of_xlsx': [
  'Find the EIA battery-generator failure in optima-specialist-daily.service and its manifest; identify the requested workbook URL and saved HTTP response.',
  'Inspect redirects, HTTP status, content type and XLSX signature. Locate the official replacement workbook if the source URL changed; retain the HTML response as failure evidence.',
  'Inspect the eia_xlsx adapter in specialist_inputs.py and EIA URL entries in config/specialist-inputs.json. Update the workbook route/parser and test one bounded download with required sheets and columns. Keep HTML validation enabled.',
  'Resume the same failed daily window. Verify its committed S3 workbook/batches and new rows in both shared and specialist Athena routes.'],
 'scrape_gateway_http_400': [
  'Inspect the NMPA service journal and failed manifest to identify the rejected page/request and gateway response.',
  'Inspect nmpa_baseline.py and nmpa_drug_trials.py. Check gateway parameter schema, encoding, target URL and pagination state against the working previous page; correct the malformed request.',
  'Resume one bounded page under the same checkpoint when the scheduled worker is idle. Retain previous committed inventory pages.',
  'Check stable identifiers, nonduplicated page advancement, S3 commit and source-filtered Athena output; close only the verified scope.'],
 'source_http_403': [
  'Identify the affected provider, sector and date from the failed service journal/manifest. Separate successful scopes from failed ones.',
  'Inspect the saved access-denied response and the Bluesky route in people_social_collection.py. Check the configured endpoint and account permissions; use a permitted search route and required authentication.',
  'Correct endpoint/access configuration and run one bounded request after the scheduled worker releases its lock. Preserve failed-scope receipts.',
  'Resume the affected checkpoint and confirm fresh S3 records plus a source/sector-filtered Athena readback. Other successful sectors do not clear this failure.'],
 'unresolved_market_coverage': [
  'Read the market daily/historical progress files and coverage-exclusions registry; enumerate unresolved symbol/date windows separately by lane.',
  'Verify exchange/ticker mappings, IPO/delisting dates, trading calendars and provider coverage against dated evidence.',
  'Repair valid mappings and replay affected windows. Add exclusions only where reviewed evidence supports that precise date scope.',
  'Verify prices/actions in S3 and Athena and reconcile unresolved counts; daily and historical symbol sets may overlap.'],
 'market_empty_price_window_unverified': [
  'Locate each empty symbol/date window in the market checkpoints; do not advance it merely because a request succeeded.',
  'Check listing history, trading days, ticker changes and provider availability with dated evidence.',
  'Retry a correctly mapped window, or record an evidence-backed scoped exclusion in the reviewed registry.',
  'Recompute unresolved daily/historical counts and verify saved prices in Athena.'],
 'historical_designation_date_unavailable': [
  'Identify the MHRA designation record and historical window in its saved manifest.',
  'Look for an official dated original list/document or permitted dated archive that establishes the designation date.',
  'If no dated evidence exists, record the date as unavailable and retain the coverage gap; do not use today’s snapshot as historical proof.',
  'Publish only supported fields with the limitation preserved, and check dependent historical features do not assume a fabricated date.'],
 'prerequisite_incomplete': [
  'Read the blocked dependent task and identify its required upstream manifest and exact universe/date scope.',
  'Resume or repair the corresponding upstream inventory/index/document window; preserve incomplete checkpoints.',
  'Require an exhausted committed upstream manifest with matching scope before restarting the dependent task.',
  'Verify dependent S3 output and Athena publication; blocked work must not become a successful empty dataset.'],
 'publication_backlog': [
  'Read the named owner’s operations/<owner>/publication-queue and publication-receipts in S3; pair entries by window/task identity.',
  'Inspect that publisher’s journal, lock state and source checkpoint. Classify queued work as waiting, partial upstream, failed validation or failed query.',
  'Let a progressing queued publisher finish. For failed entries repair the evidenced cause, then resume the existing publisher with a bounded window limit; never manufacture a checkpoint or bypass checksums.',
  'Require a current verified receipt and fresh Athena readback in the intended curated table. Recompute the backlog; shared raw readability alone does not clear it.'],
}

def steps(code):
    return GUIDES.get(code,[
      'Inspect journalctl -u <service> --since "24 hours ago" --no-pager and the named S3 checkpoint/receipt; identify the exact failed scope.',
      'Check the relevant cause: timer/schedule, lock/quota, provider access, memory limit, schema or artifact validation. Preserve original failure evidence.',
      'Apply the smallest evidenced correction and resume one bounded scope through its existing runner when the worker is idle.',
      'Verify committed S3 outputs and the appropriate Athena or model-validation receipt. Close only the verified scope.'])
