# Proceedings collection and event-source coverage

Publication resumed September 24 at the user's request after the streaming
fix and memory-budget installation. Its timer is enabled, with execution
serialized alongside other heavy jobs and a 768 MiB service cap.

The new curator validates one input batch at a time, buffers at most 64 rows
or approximately 2 MiB of encoded rows, and writes incremental Parquet row
groups. The final row can exceed the byte target; raw source/batch validation
also contributes to memory. Full-value read-back is checked in 64-row batches.
Parquet hashing, immutable upload and remote checksum read-back use bounded
reads. A publication invocation handles one window. The installed service has
MemoryHigh=512M, MemoryMax=768M and no swap allowance, with Arrow limited to
one worker thread. The hard cgroup cap also covers memory beyond Python RSS.

`conference_memory_check.py MANIFEST` validates a complete stored window and
writes local Parquet plus `reports/conference-memory-check.json`; it does not
upload or modify Athena. Run it under an equivalent memory-limited service.

Measured result (September 24): all 98,408 January 1, 2021 records validated
and curated in 286.75 seconds, with peak process RSS 216.28 MiB. This is about
94% below the user's reported 3.7 GB process usage. The separately sampled
cgroup peak reached 370.09 MiB including filesystem cache (sampling ended when
the cgroup disappeared, so this is an observed peak). The benchmark did not
publish to S3 or Athena. See `reports/conference-memory-check.json` and
`reports/conference-memory-cgroup.json`. Thirty-six regression tests passed;
bounded upload/read-back, immutability and retry behavior have unit coverage.

Implemented September 24, 2026. The active scope is collection and verification
of source records used to reconstruct events. Specialist models and HMM/TFT
inputs are deferred. An article, filing and registry update may later be linked
to one event; these collectors do not infer that equivalence automatically.

`conference_collection.py` collects all Crossref `proceedings-article` records
in bounded, exclusive daily windows. Historical collection begins January 1,
2021 using publication-date filters. Daily collection starts September 23,
2026 using publisher-update filters, so newly deposited older proceedings are
not silently missed. Crossref publication, deposit, index and meeting dates
are retained in raw metadata and must not be conflated.

The provider's JSON is stored immutably, with checksums and source URLs.
Normalized observations preserve DOIs, titles and full metadata including
authors, affiliations, event details and abstracts where supplied. Entity links
remain unresolved. Partial publication dates are retained in raw metadata;
no exact day is invented. `available_at` remains unknown: metadata retrieved
now is not proof of historical availability of every field.

The collector requires pagination exhaustion, stable provider totals, unique
DOIs and matching final counts before declaring a query complete. Each attempt
is capped at 240 pages of 500 records per lane. Incomplete attempts preserve
their committed pages but cannot advance date progress or enter publication.
Temporary provider cursors are restarted for unfinished attempts. Very large
or changing daily windows therefore remain explicit gaps; narrower partitions
or a provider snapshot are needed if they repeatedly exceed this bound.

Collection and publication timers enabled:

- `optima-conference-collection.timer`: every 30 minutes, one pending daily
  window and one historical window per run; local lock prevents overlap.
- `optima-conference-publication.timer`: configured every 15 minutes, one completed
  window, with immutable release checksums and Athena count verification.

Live database: `optima_conference_research`. Verified tables:
`conference_observations_windows` and
`conference_coverage_windows`. Query observations as versioned source records;
daily and historical searches can legitimately observe the same DOI. They are
not additive counts of distinct real-world events. Every row has
`point_in_time_eligible=false` pending separate availability verification.

Live first-pass results: the initial index-date daily query changed after
3,000 committed records and was withheld from publication. The daily filter
was changed to publisher updates. The January 1, 2021 publication query reported
98,408 records; the initial 40-page probe stored 20,000 and ended partial.
The recurring collector now uses the larger bound. Neither partial probe is
presented as complete coverage. The revised publisher-update query completed
September 23, 2026 with 4,035 observations and one coverage row, published and
Athena-count-verified at 14:03:39 UTC. Verification query:
`95655bda-7910-415c-9194-e10d73cfdd09`; release:
`e7efa7a7ae068da5d037f44eacc71d33b53b7b971b108e4b360cad48799ce08e`.

Coverage limitations: DOI-registered proceedings only. Conference websites,
non-DOI presentations and many journal-supplement abstracts remain separate
collection work. Exhausting Crossref does not establish complete conference
coverage in biotech, robotics, semiconductors or energy storage.

Protocol reference: https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/
Tests: `test_conference_collection.py` checks cursor completion, totals,
partial retry, daily update filters, uncertain dates and Parquet curation.
