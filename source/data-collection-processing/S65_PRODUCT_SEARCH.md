# S65 daily product search observations

## Current status: paused

S65 collection is paused as of 2026-10-20 at the user's request while the
company-versus-product search scope is decided. Both company and product search
services are stopped. The `optima-product-search-daily.timer`,
`optima-search-daily.timer`, and `optima-search-capture.timer` schedules are
disabled. Existing observations and query configurations are retained. Resume
collection only after the search scope is agreed; the operations below describe
the configured behavior when enabled.

`product_search_daily.py` reads the live TLS RDS `tracking.products` table daily.
The scope is every nonarchived, nonrejected product, including pending products and
rows whose older collection_enabled flag is false, as requested. It never inserts
or changes registry entities. Each canonical product name becomes one literal
query. Duplicate names are flagged and remain separate product observations;
returned pages are not automatically treated as verified product mentions.

For each product and configured search locale, one daily observation retains:

- RDS product ID, name, sector, row version, review state and query basis.
- Google SERP titles, snippets, URLs, result types, group/absolute ranks and nested
  links, plus a domain summary. Default locale: US, English, desktop, depth 10.
- A single-product global DataForSEO merged-trends request over the preceding
  90 complete days, with provider interval boundaries preserved. Includes relative
  interest over time and geographic interest by country/region where available.
  Zero may indicate insufficient data; these are not user counts or traffic shares.
- Google Ads search-volume estimates and individual monthly values, refreshed once
  per calendar month per query/locale. Missing queries are batched, up to 1,000.
  Cached values retain their original retrieval timestamp and freshness flag.
- Provider task evidence, hashes, retrieval times and the RDS directory snapshot.

The requested product is tied to its registry row in the payload; result relevance
remains unreviewed. RDS product IDs are not fabricated into the separate model
universe. Empty/suppressed data is explicitly unavailable, not fabricated as zero.
Actual visits, website analytics and referral sources remain null. Visible domains
are publishers appearing in search, not sites proven to send traffic. Geographic
interest uses the global trends scope; it is distinct from the US SERP/volume scope.
Historical interest downloaded today does not establish a historical availability
vintage. Relative series normalized over changing windows must not be stitched as
absolute counts or used to infer sales, orders, adoption or sentiment.

Records use source `dataforseo_products`, dataset `specialist_inputs`, with payload
source ID `S65` and record type `product_search_attention_observation`. They use the
existing committed collection path for S3 and subsequent Athena publication to
`optima_collected_data.observations`. The collector creates input observations;
specialist routing, model feature acceptance and training-rights review remain
separate work. No event is emitted for a routine daily search. Future attention
anomalies require a predefined causal rule and comparable query/locale/window.

## Operations

- Config: `config/product-search-daily.json`.
- Timer: `optima-product-search-daily.timer`, 12:00 Europe/Madrid plus up to five
  minutes of jitter; the shared collection lock may delay actual execution.
- Each daily run re-reads RDS, automatically including newly added products.
- Per-day product-collector spending cap: USD 1.00, including monthly keyword
  requests made that day; this is separate from the existing company-pilot cap.
  Conservative request reservations stop new calls before its remaining budget
  becomes too small. Provider response costs are audited, not assumed from row counts.
- Saved receipts prevent duplicate paid requests when replaying. An ambiguous paid
  request blocks further spending for the scope until its receipt is reconciled.
  Known provider failures are retained and not retried as new paid calls that day.
- Provider or budget limits produce explicit partial coverage and pending counts.
  Daily product ordering rotates to avoid permanently favoring the same products
  if the registry grows beyond the capped daily capacity.
- Report: `reports/product-search-YYYY-MM-DD/state.json`, also stored under
  `operations/product-search/daily/YYYY-MM-DD/state.json` in the collection store.
- An empty RDS table produces `no_products`, zero expected observations and no
  paid requests. This is a functioning empty-scope run, not product coverage.
- The worker is bounded to 20 minutes; successful product records are checkpointed
  individually. Replays use the same provider receipts and completed manifests.

Existing company-pilot search configuration remains in place, with collection
paused alongside product search. Product scope is read
from RDS and does not inherit the fixed 12-company panel.
