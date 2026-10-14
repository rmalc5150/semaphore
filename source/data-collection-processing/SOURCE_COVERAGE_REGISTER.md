# Source-by-sector coverage register

Generated 2026-09-25T06:29:09.578238+00:00.

Live S3 checkpoints and committed terminal manifests, raw-object sizes, sampled content hashes and publication receipts reconciled with local release metadata. Live Glue catalog access checked. Fresh bounded count queries for represented source pairs are linked; provider access is assessed at recorded run times, not by new paid requests.

**Scope:** All markets are in scope, confirmed September 25, 2026; no HKEX-only restriction. Company sets are collection-enabled candidates, not a final approved watchlist. IBKR excluded.

**Reading the dates:** Request boundaries are not earliest/latest usable observations. Those usable-date fields remain null until historical availability and company coverage are verified. Min/max boundaries do not prove intervening coverage. Daily freshness uses a proposed 48-hour target and a request boundary, not every company’s latest record.

Detailed files: [CSV](reports/source-sector-coverage.csv), [JSON with company/listing sets](reports/source-sector-coverage.json), [release and query receipts](reports/source-sector-coverage-evidence.json), [requirements](config/source-coverage-requirements.json).

| Sector | Collection-enabled companies | Listings | Unknown domicile |
|---|---:|---:|---:|
| biotech | 213 | 219 | 209 |
| robotics | 61 | 57 | 61 |
| semiconductors | 115 | 117 | 112 |
| energy_storage | 127 | 122 | 126 |

Counts can overlap across sectors. Source jurisdictions do not establish issuer domicile or exhaustive geographic coverage.

| Source / dataset | Sectors | Implementation | Collection / publication verification | Last stored verification |
|---|---|---|---|---|
| eodhd / company_profiles | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 7; partial/failed attempts retained; 9 verified releases | 2026-09-25T01:39:20.185193Z |
| eodhd / listing_inventory | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 2; partial/failed attempts retained; 2 verified releases | unknown |
| eodhd_market / market_records | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 2318; partial/failed attempts retained; 1168 verified releases | 2026-09-25T06:07:11.265086Z |
| hkex_prices / market_records | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 1; partial/failed attempts retained; 1 verified releases | 2026-09-24T12:53:25.292792Z |
| finlight / news_articles | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 33; partial/failed attempts retained; 5 verified releases | 2026-09-25T04:56:03.362907Z |
| marketaux / news_articles | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 28; partial/failed attempts retained; 8 verified releases | 2026-09-25T03:55:49.249938Z |
| sec_edgar / filings | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 12; partial/failed attempts retained; 10 verified releases | 2026-09-24T21:33:37.786177Z |
| hkex_news / filings | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 10; partial/failed attempts retained; 8 verified releases | 2026-09-24T23:28:51.841459Z |
| disclosure_documents / documents | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 10; partial/failed attempts retained; 11 verified releases | 2026-09-25T02:38:42.568836Z |
| disclosure_candidates / press_releases | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 10; partial/failed attempts retained; 11 verified releases | 2026-09-25T02:38:37.863092Z |
| disclosure_candidates / licensing_agreements | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 10; partial/failed attempts retained; 11 verified releases | 2026-09-25T01:33:00.827460Z |
| disclosure_candidates / ma_announcements | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 10; partial/failed attempts retained; 11 verified releases | 2026-09-25T01:52:38.186045Z |
| disclosure_candidates / strategic_transactions | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 10; partial/failed attempts retained; 11 verified releases | 2026-09-25T01:52:42.703469Z |
| clinicaltrials_gov / research_records | biotech | shared | Live committed complete versions: 10; partial/failed attempts retained; 9 verified releases | 2026-09-24T22:44:40.266166Z |
| fda_openfda / research_records | biotech | shared | Live committed complete versions: 11; partial/failed attempts retained; 10 verified releases | 2026-09-24T22:59:40.835843Z |
| ema_ctis / research_records | biotech | shared | Live committed complete versions: 10; partial/failed attempts retained; 9 verified releases | 2026-09-24T22:31:59.396667Z |
| uk_mhra / research_records | biotech | shared | Live committed complete versions: 10; partial/failed attempts retained; 9 verified releases | 2026-09-24T22:16:45.487866Z |
| japan_pmda / research_records | biotech | shared | Live committed complete versions: 10; partial/failed attempts retained; 9 verified releases | 2026-09-24T22:16:53.663297Z |
| chictr / research_records | biotech | shared | Live committed complete versions: 1; partial/failed attempts retained; 2 verified releases | 2026-09-24T19:30:38.163361Z |
| nmpa_trials / research_records | biotech | shared | Live committed complete versions: 2; partial/failed attempts retained; 2 verified releases | 2026-09-24T13:43:39.583228Z |
| google_patents_bigquery / patent_records | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 9; partial/failed attempts retained; 4 verified releases | 2026-09-24T09:51:41.703895Z |
| uspto_odp / patent_records | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 1; partial/failed attempts retained; 0 verified releases | unknown |
| crossref_proceedings / conference_records | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 22; partial/failed attempts retained; 23 verified releases | 2026-09-25T06:26:34.836117Z |
| people_rss / people_source_records | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 12; partial/failed attempts retained; 19 verified releases | 2026-09-25T06:27:50.922530Z |
| personnel_archive / people_source_records | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 88; partial/failed attempts retained; 101 verified releases | 2026-09-25T06:28:18.650696Z |
| reddit / social_records | biotech, robotics, semiconductors, energy_storage | legacy only; shared migration pending | not evidenced by this inventory; 0 verified releases | unknown |
| bluesky_search / social_records | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 0; partial/failed attempts retained; 0 verified releases | unknown |
| search_rankings / search_rankings | biotech, robotics, semiconductors, energy_storage | not implemented | not evidenced by this inventory; 0 verified releases | unknown |
| guidelines_payer_policies / required_source_gap | biotech | dedicated collection not verified | not evidenced by this inventory; 0 verified releases | unknown |
| kol_disclosures / required_source_gap | biotech | dedicated collection not verified | not evidenced by this inventory; 0 verified releases | unknown |
| trial_site_history / required_source_gap | biotech | dedicated collection not verified | not evidenced by this inventory; 0 verified releases | unknown |
| milestone_timelines / required_source_gap | biotech, robotics, semiconductors, energy_storage | dedicated collection not verified | not evidenced by this inventory; 0 verified releases | unknown |
| additional_conference_abstracts / required_source_gap | biotech, robotics, semiconductors, energy_storage | dedicated collection not verified | not evidenced by this inventory; 0 verified releases | unknown |
| uspto_odp / patent_assignment_records | biotech, robotics, semiconductors, energy_storage | shared | Live committed complete versions: 2; partial/failed attempts retained; 0 verified releases | unknown |
| nmpa_trials / registry_inventory | biotech | shared | Live committed complete versions: 0; partial/failed attempts retained; 0 verified releases | unknown |

## Remaining verification

- Reconcile every required company/query/date against committed S3 checkpoints, including uncurated, failed and partial runs. Local receipts cannot enumerate all raw collections or missing periods.
- Refresh live source access, Glue partitions and daily freshness; the register preserves the actual receipt verification time rather than treating this build time as a new verification.
- Establish point-in-time usable dates and required company/geography scope. Sector applicability is not sector completeness.
- Close Reddit and search-ranking historical access gaps, regulatory/site/KOL/policy gaps and broader conference coverage.
- Refresh with `.venv-athena/bin/python source_coverage_register.py`; no collection schedules or source state are changed.

## Live reconciliation

Read [findings and limits](COVERAGE_RECONCILIATION.md), [exact query/date gaps](reports/live-coverage/query-date-gaps.csv), and [machine-readable reconciliation](reports/live-coverage/reconciliation.json).

Live snapshot completed 2026-09-25T05:54:59.809324+00:00. Source success times, failed-attempt reasons and raw checkpoint status are included in the register CSV/JSON. Unknown point-in-time usable dates remain unknown.
