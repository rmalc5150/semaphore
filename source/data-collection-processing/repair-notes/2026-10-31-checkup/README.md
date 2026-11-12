# October 31 checkup — repairs and owner actions

## Repaired and deployed

- **FRED / ALFRED:** live evidence shows the older T10Y2Y request includes 2,675 vintage dates, exceeding the provider's 2,000 limit. The adapter now paginates through contiguous, bounded realtime intervals even for retained older job specifications. It preserves vintage intervals and validates cumulative counts. Live replay of its first segment returned 261 observations and a continuation cursor. It is not a complete backfill or Athena verification.
- **DataCite:** oversized pages now retry with 100, 10, then one record, retaining filters and cursor position. Authentication and other failures do not trigger page-size retries; a single oversized record remains a visible failure. A live first-page probe of the failed July 2016 dataset scope returned 100 records and a continuation cursor. That probe did not encounter an oversized response; reduction is regression-tested.
- **Unavailable FRED vintage:** the DTWEXBGS query returned an explicit provider message that the requested ALFRED series/vintage is unavailable. The adapter now records `fred_vintage_unavailable` instead of generic HTTP 400. No current data is substituted for missing historical vintages, and no broad history exclusion was added.

Deployment succeeded to 149 historical-worker module copies and 16 local daily-workspace copies, for subsequent invocations. No jobs or schedules were stopped. Existing owner pauses remain intact. 39 tests passed. An older bioRxiv test fixture was updated for the already-existing 20-PDF processing limit; production bioRxiv behavior was not changed.

Evidence: `fred-probe.log`, `live-probes.json`, `tests.log`, `deployment-result.json`.

## Your actions

### 1. USGS permission repair — approved and completed

The owner explicitly approved `artifact-policy-proposed.json`. Applied it only after confirming the live policy still matched `artifact-policy-before.json`; read-back matched the exact approved proposal.

It adds only `s3:GetObject` and `s3:PutObject` to role `constellation-backfill-worker`, under these existing collector metadata paths in bucket `data-collection-059416028963-us-east-1-an`:

- `research-data/operations/usgs-minerals/directories/*`
- `research-data/operations/usgs-minerals/report-heads/*`
- `research-data/operations/usgs-minerals/reports/*`

No deletion rights, other source prefixes, secrets permissions or existing deny rules change. The worker would gain permission to read and overwrite metadata in those paths. Automatic approval review initially required explicit approval, which the owner subsequently supplied. **Applied and verified:** live GetObject/PutObject tests succeeded under the production worker role for all three paths, using separate permission-verification objects and without modifying production records. See `artifact-policy-applied.json` and `usgs-permission-verification-result.json`. This verifies access, not a full collection replay or Athena publication, and does not fix USGS HTTP 404 archive URLs.

The separate `RAW_SOURCE_AUDIT_T3_PERMISSIONS.md` policy visible in the IDE is for an audit runner; it is not this collection permission repair. Do not replace either policy with the other.

### 2. Confirm or replace the Census key if not already done

The October 30 live probe redirected the stored key to `/data/invalid_key.html`. Today's supplied report still contains older failed Census scopes; it is not a fresh credential test.

1. Check the Census API-key registration email and complete activation if required.
2. Store the issued value in field `US-census` of the existing `dataSourceAPIkeys` secret.
3. Tell me it is updated; do not paste the value here. The exact trade request can then be retested.

## Remaining engineering work — no new owner purchase requested

- Verify scheduled replay/checkpoints and Athena publication for repaired FRED/DataCite scopes; source probes alone do not close earlier gaps.
- Locate and validate USGS historical archive URLs; 404 does not prove absent data.
- Resolve TED's exact denied artifact path and replay interrupted scopes.
- Replay FDA windows with the repaired parser; investigate HTTP 400 windows separately.
- Resolve ClinicalTrials source-count mismatches without accepting truncated results.
- Review the precise unavailable FRED vintage intervals before accepting any permanent gaps.

No monitoring failures were manually cleared on the strength of these probes. SMS remains resolved per the owner's confirmation. Pre-launch medRxiv exclusions remain in place.
