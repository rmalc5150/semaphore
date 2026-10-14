September 25 update: nine feeds are active after verified additions of Robohub (75 articles), EE Times (10) and pv magazine (10). Retrieval 2.1 fixes hyphenated layoffs and plural-role misses and retains explicit context flags. Publication now handles up to 12 windows after eight archive windows per run, under the same 256 MiB cap. See reports/personnel-retrieval-review-2026-09-25.json. All 95 added feed articles are Athena-count-verified (reports/personnel-new-feed-publication.json). Earlier counts below describe the initial rollout.

# Personnel source collection

Operational September 24, 2026. Collect source records for later event creation;
do not interpret retrieval matches as confirmed hires, departures or employment.

## Current feeds and archived sources

Six verified feeds cover biotech (BioSpace, BioSpace Job Trends, Fierce Biotech),
robotics (The Robot Report), semiconductors (Semiconductor Engineering), and
energy storage (Energy Storage News). Today's snapshots contain 223 articles,
stored with the raw feed and verified in Athena. These are all feed articles,
not 223 personnel announcements. RSS snapshots cannot establish past coverage.

`personnel_archive.py` scans completed Finlight and Marketaux news windows,
disclosure documents, HKEX filing records, and these feeds. The date floor is
January 1, 2021. Source lanes rotate, with oldest windows first within each
lane. The first two runs examined 16 source windows, including January 2021
news, June 2024 filings and September 2026 news/filings/feed snapshots.
See `reports/people-archive-initial-verification.json` for individual counts.
Different source windows can contain the same announcement: totals are not
counts of distinct people or movements.

English role/movement terms, Chinese appointment/departure terms and SEC Item
5.02 retrieve unreviewed candidates. Original records, parent manifest, raw
document references, dates and identifiers are preserved. Unknown dates are
counted separately and excluded; no historical availability date is invented.
Company/person links remain unresolved unless already supported by the parent.
Retrieval can miss announcements or return false positives.

## Operation and verification

`optima-people-collection.timer` runs at minutes 19 and 49 UTC. Its service
executes feed capture, eight archive windows, then at most twelve people
publication windows sequentially. It has a 256 MiB cap inside the shared
2,000,000,000-byte data slice. This bounded worker may overlap one serialized
heavy job. Use the managed service rather than an uncapped manual collector.

Archive input is validated before candidate publication, with disk spooling,
small commits and resumable checkpoints. The observation curator uses small
Parquet row groups, bounded upload/checksum reads and complete read-back
validation. A shared publication lock defers conflicting publisher runs.

Athena database: `optima_people_research`; tables:
`source_observations_windows` and `source_coverage_windows`. Filter by source:
`people_rss` contains feed observations; `personnel_archive` contains retrieval
candidates. Both remain ineligible for point-in-time modeling until availability
is verified. Initial archive publication at 21:10 UTC verified four partitions,
12 candidate observations and four coverage rows, including two zero-match
windows. Queries: `eeeae75e-a233-4a85-a522-ef519114820b`,
`e15ff992-b6f7-4c25-906a-9bee85d08651`,
`49a9452e-d8a9-41df-a104-f710d0321047`,
`8df0bc6a-8846-41a1-8295-804e69bf9169`.

The first two managed runs finished all three stages successfully. Twenty-one
focused regression tests passed, including interrupted archive resume without
duplicate candidates, source validation, immutable streaming publication and
the aggregate memory-budget calculation.

## Remaining coverage

Historical collection depends on the underlying news and filing backfills;
2021–present personnel history is not complete. A zero lexical-match count
does not prove no personnel events occurred. Archive source records can overlap
and need later event linking and review. Feed collection covers these selected
publishers, not every company or all four sectors exhaustively.

Bluesky search returned HTTP 403 for all four sectors and is not part of this
active workflow. Another robotics feed exhausted timeout retries. Broader
social access and historical personnel coverage remain explicit gaps.
