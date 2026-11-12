# S47 original evidence, product matching and events

Installed October 18, 2026. The daily landing-page adapter now extracts substantive text and relevant links while preserving original HTML. Two capture modes retrieve linked evidence; a separate matcher consults the live RDS products directory and emits reviewable evidence-event candidates. The isolated `event_pilot.py` experiment is unchanged.

## Jobs

| Script/service | Operation |
|---|---|
| Existing `specialist_inputs.py` S47 adapter `nist_robotics` | Captures original landing HTML and extracts text, tables and relevant links. Old snapshots remain intact. |
| `nist_robotics_pipeline.py --mode daily` / `optima-nist-robotics-daily.timer` | Waits for a completed S47 landing capture today in Europe/Madrid, then builds and resumes its linked-evidence queue. |
| `nist_robotics_pipeline.py --mode backfill` / `optima-nist-robotics-backfill.timer` | Replays the pinned ten saved landing observations, discovers their links, retrieves currently available originals and sends the verified completion email. |
| `nist_robotics_match.py` / `optima-nist-robotics-matching.timer` | Runs after completed evidence capture; reads RDS products, aliases and related company names, saves mention matches and emits deduplicated pending-review events. |

Capture timers resume every five minutes after the previous invocation ends. Matching probes every 15 minutes and processes each completed capture job at most once per Madrid day. An initial backfill match can follow backfill completion; later recurring rechecks require today's completed daily evidence scope. Old unfinished daily capture work is resumed before a new scope is opened. Locks prevent overlapping writers. Services use bounded invocations, memory and CPU limits.

## Evidence collection and scope

Initial scope is [pinned here](reports/nist-robotics-backfill-2026-10-18/input-batches.json); controls are in [config/nist-robotics.json](config/nist-robotics.json). The current scope follows relevant NIST-hosted links to depth three, at most 150 URLs per capture job, with eight documents per invocation and a 32 MiB accepted-document size cap. Retrieval itself also has the shared response-size cap. This is a bounded robotics evidence inventory, not all NIST pages or a complete historical publication archive. Links outside supported hosts/types are not crawled; frontier URLs beyond depth/count limits are explicitly recorded. Future broader source coverage requires deliberate scope changes.

Original HTML, PDF, CSV, JSON and ZIP responses are saved to immutable S3 source evidence with SHA256, URL and retrieval time. HTML extraction removes navigation and retains substantive text, headings and tables. PDF extraction retains page text; scans without sufficient text are flagged `ocr_needed`, not treated as extracted benchmark results. NIST JSON dataset metadata is parsed for distribution download/access links. CSV/JSON originals are retained in full within the size cap, with a limited sample index; ZIP originals are retained with a member index, without claiming member-level analytical extraction. Unsupported formats and external-host datasets remain gaps in scope. Extracted text indexes over 2 MiB are truncated and flagged; originals remain archived. There is no OCR/model-based measurement interpretation in this implementation.

A failed document retries up to three times with a 15-minute delay, then becomes an explicit gap. The completion receipt includes retrieval errors, depth/count exclusions and extraction-status counts. URLs with malformed links, unavailable files, provider failures or size limits are not silently called successful.

Saved older landing HTML is original historical evidence. A linked PDF fetched now is evidence retrieved now: the pipeline cannot reconstruct an earlier linked version that was never saved. Source publication dates, retrieval dates and current registry associations remain separate.

## RDS product matching

`rds_company_directory.read_directory('products')` reads a consistent read-only transaction over verified TLS from `tracking.products`, `product_aliases` and related companies. No local universe file substitutes for the RDS product directory. The reader uses the existing RDS-managed credential route and performs no registry writes.

Only verified, unarchived robotics products and applicable verified aliases nominate resolved-ID mentions. Exact word boundaries prevent substring model matches. Short/generic single-word names require a related company name in nearby text; otherwise they remain ambiguous candidates. Alias validity uses the explicit document day when extracted, otherwise the current check day. Product associations are reported with matched text, character location, context and match basis. Unknown robot names cannot be resolved until the directory contains suitable identities/aliases; no product identities are invented.

The RDS product directory had zero products, aliases and product-company links when checked at installation. Accordingly, the initial corpus will produce unresolved/no-product-match outcomes and no tracked-product events until verified products are added. Subsequent eligible daily checks reconsider saved evidence against the latest directory.

Top-level shared observation `product_ids` remain empty because the static observation contract's universe is separate from the live RDS directory. RDS IDs are explicit in `payload.data.matches[*].product_id` and `payload.data.product_ids` for events, with directory snapshot hashes. These are mention associations, not silently promoted entity claims.

## Event semantics

For publication/PDF/method evidence with a sufficiently specific tracked-product mention, emit `robotics_research_evidence_observed` with `status=candidate`, `review_status=pending`, original source references and match context. A publication date is attached only when explicitly parsed from source metadata; otherwise occurrence remains unknown. No historical model eligibility is inferred.

The event means that source evidence mentioning the product was observed. It does **not** mean the product was tested, achieved a numeric result, received certification, launched or was independently validated. Reference-list mentions and test-subject mentions require review to distinguish. General project/discovery pages, ambiguous names, poor extraction and unmatched products do not emit these events. Full dataset files can be captured without an event when no adequate textual product evidence is extracted.

Event identity uses source URL plus normalized semantic document content; product bindings are versioned separately. Repeated downloads or navigation-only HTML changes do not produce another event for unchanged content/bindings. A substantive text change can produce another pending-review evidence observation, not an automatic conclusion that the benchmark improved. Event versions are saved once with replay-safe collection task identities. Newly adding a product to RDS can link old evidence now; the match timestamp does not turn it into a new historical publication.

## Backfill completion email

Recipient: `randall@optima-holdings.com`, using the existing confirmed SNS topic. Success waits for all queued documents to reach downloaded or explicit-gap outcomes, initial product matching to finish, committed document batches to be verified by the shared publisher, and exact document plus distinct document-mapping counts in Athena. Completion with gaps identifies them and reports scoped exclusions and extraction limitations. The email describes evidence candidates, not verified product performance. SNS message-ID persistence suppresses ordinary repeat sends; a crash exactly between SNS acceptance and saving the ID can repeat a notification.

Capture and matching outcomes remain separate: lack of tracked products is an unresolved directory state, not a failed download and not a reason to invent an event. The backfill can complete with disclosed gaps and zero matches.

## Outputs and checks

- Local durable task database: `nist-robotics.sqlite3`.
- Status: `reports/nist-robotics-backfill-latest.json`, `nist-robotics-daily-latest.json`, `nist-robotics-matching-latest.json`.
- S3 operational prefix: `research-data/operations/nist-robotics/`, including per-job capture/completion receipts, product-directory snapshots and event-version manifests.
- Original bytes: `research-data/source_documents/nist_robotics_documents/<sha256>`.
- Shared Athena view: `optima_collected_data.observations`, dataset `specialist_inputs`, sources `nist_robotics_documents`, `nist_robotics_product_matches`, `nist_robotics_events`. These appear after committed-data publication, separately from the original `nist_robotics_methods` landing snapshots.

Inspect `journalctl -u optima-nist-robotics-backfill.service`, the daily/matching services, SQLite queue counts and status receipts. A timer being active is not proof of complete evidence coverage. `test_nist_robotics.py` covers content selection, safe links, source tables/data, semantic deduplication, word-boundary and ambiguity matching, review filters, non-benchmark event semantics, queue limits, the empty-anchor regression and email gating. Use the updated S47 SQL checks to inspect the saved evidence and candidate events.
