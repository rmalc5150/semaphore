# S65 product-search directory repair — November 10, 2026

Affected service: **`optima-product-search-daily.service`**, the DataForSEO collector for product search attention, visible search-result domains, monthly keyword volumes and relative search interest/geography. It is separate from EMA CTIS and does not measure actual visits or referrals.

## Root cause

`rds_company_directory.read_directory('products')` queried `tracking.products`, aliases and company links on the old RDS instance. The `tracking` schema was deliberately retired when the new `metadata_engine` control plane/graph was introduced. This was an obsolete dependency, not a failed API key or an accidentally missing database to recreate.

Read-only inventory confirms the replacement schema exists, but currently holds only organization/publication entities: **zero product entities**. The only saved product-search directory snapshot is also empty. The synthetic `tracking_trial_20261014` schema is not a production directory and was not used.

Owner clarified: **track all products for Constellation**, not a manually selected product watchlist.

## Implemented repair

- Configured `directory.mode=metadata_engine`. New `product_search_directory.py` reads **all named active/provisional product entities** and their nonrejected, currently valid names from the existing Constellation metadata registry using its existing scoped runtime connection. No old tracking/master connection is used on this path.
- Selects a deterministic primary name, retains aliases and existing entity UUIDs, includes provisional candidates and does not infer ownership or sectors. Candidate identity is not promoted to verified identity. No manual product subset is configured.
- When the registry is empty, writes **`pending_dependency / product_directory_required`**, `capture_ready=false`, unknown coverage/expected counts and zero paid requests/cost. Empty input is not certified as completed collection.
- Added a lightweight service preflight so an empty registry does not reserve shared RAM/capture locks while waiting for input. When named products become available, it executes the original supervised command with existing S3 checkpointing, shared locks, request limits and **$1/day** budget intact.
- Persisted the service drop-in under `systemd/optima-product-search-daily.service.d/zzzzz-product-directory.conf`, installed it, reloaded systemd and ran the actual production service successfully. Only its earlier lock-waiting invocation was stopped; no capture child or other pipeline was interrupted.
- **12 tests passed**: existing collection/replay/budget checks plus pending-input/no-paid-call behavior, all-product candidate inclusion, alias/identity preservation and populated-directory supervisor handoff.

## Verified live outcome

Production service completed with **exit 0 / Result=success**. Its daily timer remains enabled and active. Actual S3 readback confirms the pending dependency and zero DataForSEO requests:

` s3://data-collection-059416028963-us-east-1-an/research-data/operations/product-search/daily/2026-11-10/state.json `

See `live-status.json`, `service-status.txt`, `service-journal.txt`, `timer-status.txt` and `tests.log`.

The repeated missing-database exception is repaired. **Product collection is not yet producing observations** because the replacement registry has no products. No product-search Athena rows were fabricated or certified by this repair.

## Remaining engineering work

Populate Constellation product entities/names from source-supported product discovery, retaining provider identifiers, original source observations and candidate provenance. The current metadata graph extraction does not yet create product entities. A source's raw product fields alone do not make it a registered product automatically.

Once named product entities exist, the next scheduled invocation includes all of them automatically. Verify request receipts, budget-bounded coverage, raw commits and subsequent Athena publication before declaring this source collecting end to end. Large all-product universes can exceed the existing $1/day allowance; partial coverage must stay explicit. No new subscription, restoration of the retired schema or manually chosen product list is required for the directory repair.
