# EODHD company universe integration

The Secrets Manager ARN is stored in `config/eodhd-universe.json`. The API key
is loaded at runtime and is excluded from configuration files, public source
URLs, evidence, task scopes, failures and logs.

## Live status

The expanded profile, review and universe releases are live in Athena database
`optima_eodhd_research`, workgroup `optima-eodhd-research`. Profile coverage is
9,438 symbols, including a completed 7,900-profile cohort across all 66 selected
exchange codes. Review records 515 supported decisions across 492 listing
symbols, 35 rejected matches and 329 needing more evidence. Versioned universe
0.2.0 contains 494 companies; 101 identities are registry-corroborated and 393
remain pending. There are still 132,346 inventory symbols without profiles and
3,485 collected profiles without usable descriptions. A quota-safe daily timer
is enabled for subsequent cohorts. See [EODHD_ATHENA.md](EODHD_ATHENA.md) and
[COMPANY_UNIVERSE.md](COMPANY_UNIVERSE.md) for releases, findings and SQL.

On September 22, 2026, active and delisted common-stock inventory collection
completed all 132 requests across 66 selected provider exchange codes, saving
141,783 listing records (72,940 active and 68,843 delisted). The committed manifest is
`manifests/collection_runs/source=eodhd/dataset=listing_inventory/run_4accc263-2cce-4a36-a647-e63d955517c5/final.json`.
This is completion of the specified provider inventory, not proof of every
exchange worldwide or a count of unique companies. Fundamentals collection,
sector classification review and identity reconciliation remain separate.
The verified exchange counts are in `reports/eodhd-inventory-2026-09-22.json`;
this inventory-only report deliberately has no profile inputs attached.

The earlier US/Hong Kong profile scan was resumed from its September 18 task
on September 22 and added 500 records, bringing that scan to 510 of 21,336
symbols. Its latest manifest is
`manifests/collection_runs/source=eodhd/dataset=company_profiles/run_ff5b171a-795d-47c7-aaa2-e9e9025e8ea5/final.json`.
The run stopped intentionally with `partial: record_limit`. Use this latest
manifest with `--resume-manifest` for the next batch. No recurring job has been
installed. The expanded 141,783-listing inventory is a separate snapshot from
the original 21,336-symbol cohort being scanned.
The verified profile report is `reports/eodhd-profile-coverage-2026-09-22.json`.
All 510 profiles are available. The rules nominate 44 listing symbols with 46
overlapping sector memberships: biotech 8, robotics 13, semiconductors 13 and
energy storage 12. Four profiles lack descriptions; 466 have no rule match.
These are candidates and coverage gaps, not reviewed company classifications.

On September 18, 2026, `/api/user` reported a paid monthly subscription and a
100,000-call daily limit. Current `fundamentals/{SYMBOL}?filter=General` requests
worked for MRNA.US, ISRG.US, NVDA.US and QS.US. Their immutable collection run
completed with four records. This confirmed that classification must inspect
the description as well as industry fields: ISRG is not labelled robotics in
its broad industry, while QS is not labelled energy storage there.

The screener returned HTTP 403 in the September 18 checks. Bulk-fundamentals
access has not been established for the correctly versioned endpoint. The
integration uses the entitled exchange-symbol inventory plus
individual General profiles. The configured cost is ten API calls per General
profile, observed from the account usage counter; every batch checks current
usage and preserves 5,000 calls of daily capacity.

The live active-listing pilot completed with 21,336 common-stock records:

```text
manifests/collection_runs/source=eodhd/dataset=listing_inventory/
run_dc7390c4-e71f-48a1-b52d-abbf33d4d470/final.json
```

It contains 17,829 US and 3,507 Hong Kong provider listings. The provider's
current exchange directory contains 65 physical exchanges and five virtual
asset markets. Hong Kong's symbol endpoint works but HK is absent from that
directory, so `config/eodhd-universe.json` records HK as an explicit validated
supplement. This distinction prevents the result from being described as more
complete than the provider directory establishes.

The follow-on live check fetched ten available General profiles from this
inventory and saved them in
`manifests/collection_runs/source=eodhd/dataset=company_profiles/run_a17eb1c2-d0d6-40a9-9b51-63472a5c3568/final.json`.
All batch and evidence checksums were verified, and the committed checkpoint
has cursor `10`. Its `partial` / `record_limit` status is the intended stop
after ten symbols; the inventory-wide scan remains unfinished. Shared
inventory evidence is downloaded and checksum-verified once per distinct
object/checksum in each validation pass, avoiding repeated downloads for every
listing. Local EODHD tests cover shared-evidence reuse and rejection of
subsequently corrupted evidence, as well as cohort collection and review.

## Collection stages

`inventory` takes current active and/or delisted common-stock snapshots. The
exact exchange directory response, selected exchanges, status sets and
instrument type are part of task identity. Each exchange/status response is
stored as immutable source evidence and committed as a resumable page.

```bash
# All physical exchanges returned by the provider, plus validated supplements;
# active and delisted are both included by default.
.venv-athena/bin/python eodhd_universe.py inventory

# Bounded pilot or targeted refresh.
.venv-athena/bin/python eodhd_universe.py inventory \
  --exchange US --exchange HK --inventory-status active
```

`inventory-profiles` accepts only a complete, committed inventory manifest. It
verifies the manifest, configuration hashes, batch checksums, record envelopes
and source-evidence checksums before deriving symbols. Each profile is a
separate checkpoint. On the same UTC day the command resumes automatically;
across UTC days, supply `--resume-manifest` with the latest partial/failed
profile manifest to preserve the original task identity and cursor. Without
that flag, a new day creates a new current-profile task. Use the same inventory,
sector rules, universe, taxonomy and delisted selection when resuming.

```bash
.venv-athena/bin/python eodhd_universe.py inventory-profiles \
  --inventory-manifest manifests/collection_runs/source=eodhd/dataset=listing_inventory/RUN/final.json

# Include symbols that were delisted at the inventory snapshot.
.venv-athena/bin/python eodhd_universe.py inventory-profiles \
  --inventory-manifest manifests/collection_runs/source=eodhd/dataset=listing_inventory/RUN/final.json \
  --include-delisted

# Continue an incomplete profile scan on a later UTC day.
.venv-athena/bin/python eodhd_universe.py inventory-profiles \
  --inventory-manifest manifests/collection_runs/source=eodhd/dataset=listing_inventory/RUN/final.json \
  --resume-manifest manifests/collection_runs/source=eodhd/dataset=company_profiles/LATEST_PARTIAL_RUN/final.json \
  --max-records 500
```

An explicit resume verifies that the manifest is still the latest terminal
checkpoint, rejects changed scope and preserves the earlier task window.
Each newly fetched profile retains its actual ingestion timestamp; continuing
an older task does not backdate the new observations. Progress messages report
each committed exchange/status page and each hundred newly committed profiles.

`eodhd_coverage.py` creates a local JSON report from committed inventory and
profile manifests. Incomplete profile manifests are accepted for progress
reporting and remain labelled partial/failed; they are not promoted into a
complete dataset. It verifies record, batch and evidence integrity, deduplicates
inherited observations by provider symbol, and reports sector matches as
pending candidates. Profiles without rule matches remain unclassified rather
than being declared outside the requested sectors.

```bash
.venv-athena/bin/python eodhd_coverage.py \
  --inventory-manifest manifests/collection_runs/source=eodhd/dataset=listing_inventory/RUN/final.json \
  --profile-manifest manifests/collection_runs/source=eodhd/dataset=company_profiles/RUN/final.json \
  --output reports/eodhd-coverage.json
```

By default, the profile stage uses the remaining daily allowance while
preserving 5,000 API calls, capped at 10,000 symbols per attempt. It can be
lowered with `--max-records`; this is a per-attempt cap and does not change task
identity. A partial run resumes at the next uncommitted symbol. HTTP 404 profile
results are retained as explicit, evidence-backed `not_found` coverage outcomes
rather than being mistaken for successful empty profiles.

The explicit-symbol command remains useful for review cohorts:

```bash
.venv-athena/bin/python eodhd_universe.py profiles \
  --symbol MRNA.US --symbol ISRG.US --symbol NVDA.US --symbol QS.US
```

## Sector and identity handling

Classification examines Industry, GICS industry, GICS subindustry and the
business description. It supports overlapping candidates for biotech,
robotics, semiconductors and energy storage. Energy storage includes batteries,
supercapacitors, thermal, mechanical and hydrogen storage; generic cloud
storage, power generation and hydrogen production do not match by themselves.

Every match includes the field, matched text and an excerpt, and remains
`pending` until reviewed. Exact company-name matches are also candidates, not
verified links. Current provider labels do not prove historical sector
membership and are never backdated.

EODHD is a listed-security source. A completed scan can establish coverage of
the pinned EODHD listing inventory, but it cannot establish coverage of private
companies. Private-company discovery and identity reconciliation remain a
separate input to the shared universe. The existing 20 company IDs are retained
until the candidate review and promotion stage creates the next universe
version.

## Next release work

1. Refresh the completed active/delisted inventory when a new snapshot is needed.
2. Resume quota-aware General-profile batches until every inventory symbol has
   an available or explicit unavailable outcome.
3. Extend the verified Athena research and review releases as new cohorts
   arrive, using explicit catalog updates or versioned tables. Review missing
   descriptions and suspect provider classifications before promotion.
4. Reconcile listings, legal companies, ADRs and duplicate cross-listings;
   preserve existing UUIDs and create each new company ID once.
5. Promote reviewed memberships into a new shared-universe version, then point
   every sector-filtered collector at that pinned version.

Primary provider documentation:
[exchange and ticker lists](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours),
[fundamentals](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds),
[API limits](https://eodhd.com/financial-apis/api-limits),
[screener](https://eodhd.com/financial-apis/stock-market-screener-api), and
[bulk fundamentals](https://eodhd.com/financial-apis/bulk-fundamentals-api-via-extended-fundamentals-plan).
