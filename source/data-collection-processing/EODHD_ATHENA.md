# EODHD research and review in Athena

Database: `optima_eodhd_research`  
Workgroup: `optima-eodhd-research`  
Region: `us-east-1`

## Latest verified publication: September 22, 2026

The expanded research, review and company-universe releases are live. Thirteen
Athena verification queries passed, including coverage, observation joins,
identity status, sector status and private-discovery counts. The final local
regression run passed 146 tests across the shared pipeline.

| Measure | Result |
|---|---:|
| Inventory listings | 141,783 |
| Profiles in the latest cohort | 7,900 |
| Combined profile symbols | 9,438 |
| Inventory symbols with a profile outcome | 9,437 |
| Inventory symbols not yet collected | 132,346 |
| Supported sector decisions | 515 |
| Rejected sector matches | 35 |
| Sector decisions needing more evidence | 329 |

The 515 supported decisions cover 492 listing symbols, which reconcile to 477
modeled companies. Universe version 0.2.0 contains 494 companies including the
20-entry seed, 492 listings, 655 aliases, 984 external identifiers and 497
verified sector memberships. Registry checks corroborated 112 supported listing
identities; after grouping and conflicts, 101 company entities are verified and
393 remain pending. There are 3,485 available profiles without usable business
descriptions and 42 inventory/profile identifier conflicts.

| Sector | Supported | Rejected | Needs more evidence |
|---|---:|---:|---:|
| Biotech | 219 | 3 | 101 |
| Robotics | 57 | 1 | 45 |
| Semiconductors | 117 | 7 | 99 |
| Energy storage | 122 | 24 | 84 |

Prior manual decisions remain pinned to their observations. New candidates use
conservative rules; uncertain matches stay `needs_more_evidence`. CIK and LEI
checks use SEC and GLEIF, and name mismatches remain pending. The stable-ID
registry is included in the immutable universe release.

Research release:
`f0e8983c840f2e0ed6e6787174ea9cba4e95c4508bcf22b3e6a0e448ddb0939b`.
Review release:
`39495eb7f0f5e3313fb03e06946424b4d240bcd6d6f9761b51cacaae887f0eaa`.
Company-universe release:
`233005bc22883a72cc6e9754b7a81e9495f83b276904a201ea3e4b785880d016`.
Their S3 locations are under
`s3://data-collection-059416028963-us-east-1-an/research-data/curated/`,
in `eodhd/releases/RESEARCH_ID/`, `eodhd_reviews/releases/REVIEW_ID/`, and
`company_universe/releases/UNIVERSE_ID/`.
Local release directories are `eodhd-athena-build/RESEARCH_ID/` and
`eodhd-review-build/REVIEW_ID/`; each contains `athena-verification.json`.
The review directory also contains `sector_reviews.csv` and
`company_reviews.csv`. Exact decisions are in
`unused/reports/eodhd-sector-decisions-2026-09-22-cohort-2.json`.

The publication uses the September 22 inventory of 141,783 active and delisted
common-stock listings across 66 selected provider exchange codes. Profiles
combine the earlier samples and two broad cohorts, including the latest 7,900
symbols spread across exchange/status groups. This is a
partial profile scan of the inventory. It does not claim full global company
coverage, private-company coverage or historical sector membership.

The exact inventory and profile manifests are pinned in
`config/eodhd-athena.json`. Preparation validates committed manifests, record
envelopes, source evidence and batch checksums, then checks Parquet round trips.
Publication uses immutable S3 prefixes under `research-data/curated/eodhd/`.
Successful deployment writes an `athena-verification.json` with `status:
verified` in the local release directory and an immutable verification object
beside the S3 release. Preparation or upload alone does not mean queries passed.

## Research tables

| Table | Contents |
|---|---|
| `listing_inventory` | Every inventory listing, its active/delisted status and profile coverage |
| `company_profiles` | Latest observed profile/outcome per symbol within the pinned inputs |
| `sector_candidates` | Original textual matches, with excerpts and observation IDs |
| `company_identity_review` | Provider identifiers, inventory comparisons and reconciliation flags |
| `exchange_coverage` | Collected, unavailable and uncollected counts by exchange/status |
| `collection_runs` | Input manifest status, including the deliberately partial earlier scan |

The review release adds `sector_reviews` and `company_reviews` to the same
database using a separate immutable prefix. `sector_reviews` records explicit
supported/rejected/needs-more-evidence decisions tied to profile observation IDs.
`company_reviews` records identity screening findings. Neither table silently
merges companies or changes shared-universe IDs. Original candidates remain
available for comparison with the reviewed decisions.

```sql
SELECT exchange_code, listing_status, inventory_records,
       profiles_available, profiles_unavailable, profiles_not_collected
FROM optima_eodhd_research.exchange_coverage
ORDER BY exchange_code, listing_status;

SELECT sector_id, review_status, count(*) AS listings
FROM optima_eodhd_research.sector_reviews
GROUP BY sector_id, review_status
ORDER BY sector_id, review_status;

SELECT r.provider_symbol, r.name, r.sector_id, r.review_status, r.reason,
       c.identity_assessment
FROM optima_eodhd_research.sector_reviews r
JOIN optima_eodhd_research.company_reviews c
  ON r.provider_symbol = c.provider_symbol
 AND r.profile_observation_id = c.profile_observation_id
ORDER BY r.sector_id, r.provider_symbol;
```

## Broader collection

`eodhd_batch.py plan` verifies the inventory and reusable profile manifests,
excludes already attempted symbols, and selects a deterministic round-robin
cohort across exchange/status groups. The plan pins exact symbols, input hashes
and sector rules. Four request workers fetch profiles; commits contain at most
64 records. The collector checks current account usage before each batch and
reserves capacity for retries plus the configured 5,000-call reserve. A
completed cohort is distinct from completing the whole inventory.

The latest September 22 plan is
`unused/reports/eodhd-broad-plan-2026-09-22-cohort-2.json` and its result is
`unused/reports/eodhd-broad-result-2026-09-22-cohort-2.json`. To make a subsequent
cohort, include all earlier profile manifests, including the completed broad
cohort, in the repeatable `--profile-manifest` arguments. A separate plan file
pins the next cohort. Repeating collection for a completed plan is a no-op;
partial/failed attempts resume the same task across dates.

```bash
.venv-athena/bin/python eodhd_batch.py plan \
  --inventory-manifest INVENTORY_MANIFEST \
  --profile-manifest PRIOR_PROFILE_MANIFEST \
  --limit 1024 --plan-file reports/NEXT_PLAN.json

.venv-athena/bin/python eodhd_batch.py collect \
  --plan-file reports/NEXT_PLAN.json --result-file reports/NEXT_RESULT.json
```

## Publication and review

```bash
.venv-athena/bin/python eodhd_athena.py prepare
.venv-athena/bin/python eodhd_athena.py publish --release-dir eodhd-athena-build/RELEASE_ID
.venv-athena/bin/python eodhd_athena.py deploy --release-dir eodhd-athena-build/RELEASE_ID

.venv-athena/bin/python eodhd_review.py prepare \
  --parent-dir eodhd-athena-build/RELEASE_ID \
  --decisions unused/reports/eodhd-sector-decisions-2026-09-22-cohort-2.json
.venv-athena/bin/python eodhd_review.py publish --release-dir eodhd-review-build/REVIEW_ID
.venv-athena/bin/python eodhd_review.py deploy --release-dir eodhd-review-build/REVIEW_ID
```

Deploy rejects conflicting existing table locations unless `--update-existing`
is supplied for owned tables. The immutable old release remains in S3. The
enabled `optima-eodhd-profiles.timer` collects one quota-safe cohort daily;
curated review and universe publication remain explicit release operations.

Before updating collectors' shared universe, resolve legal identities and
cross-listings, preserve existing company UUIDs, review accepted sector
memberships, and account for missing/private companies. Sector support in a
current description does not establish its historical start date.
