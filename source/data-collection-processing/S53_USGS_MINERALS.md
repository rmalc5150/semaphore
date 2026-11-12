# S53 USGS mineral report enrichment

The daily `specialist_inputs.py` adapter for `usgs_minerals` now captures one full
report per mineral/edition, rather than independent page records. It preserves
original PDFs, every page's text/layout, PDF coordinates and SHA256 source evidence.
The existing scope remains lithium, cobalt, nickel and graphite; current-year
editions are checked daily by the existing hourly specialist scheduler. Daily
checks do not imply daily statistical releases. Prior editions are retrieved for
comparisons where needed; missing prior editions remain explicit gaps.

## Six enrichment areas

1. Full report context: all pages, named sections, original/layout text, footnotes,
   default material/unit caption, footer publication precision and source hashes.
2. Structured statistics: domestic five-year series and country production/reserves
   tables, with row/column geometry, original cell, parsed decimal string, unit,
   scale, geography, reference year, estimate/revision markers and footnote refs.
   Superscript references are separated using font sizes. Wrapped price units and
   varying reserve columns are handled explicitly. `NA`, `W`, bounds and footnote-only
   cells are not silently zero. Dashes become zero only when the source defines it.
3. Supply-chain structure: domestic/world production, reserves, inventories and
   import dependence in the statistics; structured import-source shares with their
   multi-year period/material context; recycling, resource and substitution passages;
   tariff codes/rate text and structured potential stockpile acquisitions/disposals with original fiscal-year labels and gross-weight context.
   Stockpile and tariff interpretation remains source-attributed and reviewable.
4. Named developments: keyword-selected source passages for bans, quotas, openings,
   closures, restarts, cancellations and revisions, plus explicit year/month mentions.
   Temporal roles are not inferred: action dates remain unknown until reviewed.
   Named mine/project candidates retain page evidence and unresolved ownership.
5. Vintage comparisons: latest adjacent-year arithmetic changes within the report,
   absolute/relative changes and percentage-point units; same-reference-year revision
   candidates across editions; new-year and unmatched-series lists; same-edition PDF,
   statistics and text change checks against the saved operational head. Reserve
   snapshots with unknown as-of dates are not labelled historical revisions. Definition,
   scale and footnote changes still require review. Extractor versions are recorded.
6. Entity/sector links: current read-only RDS company/product snapshots, conservative
   exact multiword verified-name/alias mentions, snapshot hashes and evidence context;
   named assets and source-supported application/sector candidates. Mentions do not
   establish ownership, product chemistry or supply exposure. Generic applications
   remain unassigned sector context. There are no registry writes or automatic admissions.

At setup both RDS directories were empty. This is a disclosed unresolved exposure
state, not a download failure. Snapshot files are archived under
`operations/usgs-minerals/directories/` in the existing collection store.

PDF text/layout validation is mechanical, not independent certification of source
statistics. Missing/ambiguous units, unparsed cells, OCR needs and absent comparisons
remain explicit `review_required` outcomes. All original rows/footnotes remain
available for specialist review. Unknown revision dates and historical availability
remain unknown; report-year and retrieval-date fields are not backdated event dates.

## Backfill and completion email

`usgs_minerals_backfill.py` uses `config/usgs-minerals-backfill.json` and the pinned,
hash-checked inventory in `reports/usgs-minerals-backfill-2026-10-18/input-batches.json`:
48 committed batches / 96 original page observations at setup. Saved PDF bytes are
hash-verified and re-parsed in full. Saved prior-edition evidence is preferred over
current retrieval; a currently fetched comparison is recorded with current evidence.
Repeated captures are grouped by original page identity and PDF hash. Parent page
text, record identity, event date and lineage remain intact; new enrichment is a
new observation. Collapse `data.enrichment.report_version_id` for report-level use.

The bounded service/timer `optima-usgs-minerals-backfill` resumes every five minutes;
record failures retry up to three times with a 30-minute delay. Local status is
`reports/usgs-minerals-backfill-2026-10-18-latest.json`, with the same-named SQLite
registry. Durable job state/receipts are under
`operations/usgs-minerals/enrichment-backfill/usgs-minerals-backfill-2026-10-18/`.
Backfill does not replace operational daily heads with historical saved versions.

The established confirmed email recipient is randall@optima-holdings.com. Completion
waits for every pinned version to produce an enriched/review/gap output and for the
exact job counts to be verified in Athena. The email includes review/gap counts and
a receipt; completion with gaps does not claim complete extraction or entity exposure.

## Daily verification and downstream use

All four current reports passed live full-document extraction and prior-edition/RDS checks, yielding 386 structured cells with no unresolved cell/unit parsing gaps. These checks do not independently validate source estimates. Live end-to-end collection is recorded in
`reports/usgs-minerals-daily-live-verification-2026-10-18.json`. It exercises all four
current PDFs, previous-edition comparisons, read-only RDS snapshots and committed S3
outputs through the normal daily adapter. Source-level tests use the four original
USGS PDFs as regression fixtures. Source retrieval, extraction and publication
verification are distinct checks; the backfill completion email waits for Athena.

Use `payload.data.enrichment` on full-report daily records and enriched legacy page
records. `event_candidates` and `development_candidates` require review. The later
main event adapter must deduplicate report/page captures, retain vintages/units,
qualify material developments and resolve actual exposures before specialist dispatch.
These requirements are recorded in `ENTITY_DISCOVERY_ROLLOUT_PLAN.md#event-pipeline`; the main ledger and specialist
models are not enabled by this collection change.

Validation:
`python -m unittest test_usgs_minerals_enrichment test_usgs_minerals_backfill test_specialist_inputs -q`.
