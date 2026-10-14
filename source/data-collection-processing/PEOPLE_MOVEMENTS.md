# People movement collector

`people_movements.py` turns personnel announcements into an evidence-backed
graph-like JSON dataset and detects concentrated hiring into an organization.

Run the public feeds for a day:

```bash
python people_movements.py day 2026-08-10 --output /tmp/movements.json
```

Add a licensed, internal, or manually reviewed source as JSON Lines:

```bash
python people_movements.py month 2026-08 \
  --input-jsonl linkedin_export.jsonl \
  --feed 'Company IR=https://example.com/releases.rss' \
  --output /tmp/movements.json
```

Each input object may contain `source`, `title`, `text`, `url`, `publishedAt`,
and optionally the structured overrides `person`, `oldOrganization`,
`newOrganization`, `role`, `eventDate`, and `assets`. Structured overrides make
licensed exports deterministic while retaining their source evidence.

Company reports can also be supplied as structured observations with
`organization`, `researchHeadcount`, `asOfDate`, `source`, and `url`. The output
`workforceTrends` layer labels companies as increasing, decreasing, or stable
when at least two reported headcounts exist. Without reported counts it uses
the more cautious `likely_increasing`, `likely_decreasing`, `likely_stable`, or
`insufficient_evidence` labels based on observed R&D arrivals and departures.

Without `--output`, results go to the existing processed-data S3 bucket. Feed
failures are non-fatal and appear in `sourceErrors`; malformed local inputs and
output failures are fatal. The collector does not scrape LinkedIn or bypass
publisher access controls. Its scores rank review priority and are not factual
certainty or an investment recommendation.

Month runs additionally issue date-bounded Google News RSS searches because
ordinary RSS feeds contain only recent items and cannot backfill old months.
Use `--no-historical-search` only when supplying a complete historical JSONL
export. `coverageStatus` and `sourceRuns` distinguish a genuine empty result
from a failed/unqueried month; a run where every source returns no records now
exits nonzero after writing its diagnostic output.
