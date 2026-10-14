# Company admission and universe review

Policy 1.0 was finalized September 25, 2026. All markets and both listed and
unlisted companies are eligible. No revenue, profitability, valuation or
market-cap threshold has been agreed. Sector relevance follows taxonomy 1.0.

## Admission stages

1. **Discovered:** a traceable source identifies a potentially relevant
   organization. Record its source/reason, observed time and source dates.
2. **Sector supported:** reviewed business/product activity supports at least
   one of the four sectors. Labels, search queries and attention alone nominate
   candidates; they do not establish membership.
3. **Detailed tracking activated:** verified legal identity and sector
   membership, no unresolved identity conflict, and a dated activation decision
   in the versioned ledger. Private companies need no stock listing, but their
   identity must still be supported.

A company, listing, subsidiary and depositary receipt are different entities.
CIK/LEI links require corroboration; tickers/ISINs identify securities. Shared
names do not justify merging companies. Discovery collection can continue for
pending candidates; `collection_enabled` alone does not prove admission.

First observed time, source publication/effective dates and activation time
remain separate. Unknown earlier discovery and activation dates stay unknown.
Retrospective collection from January 2021 for today's list is not proof that
the company belonged to a historical watchlist. Preserve each old universe and
its checkpoint hash. Append suspension/reactivation decisions rather than
rewriting history.

Machine-readable policy: `config/company-admission-policy.json`.
Current state pointer: `config/company-admission-state.json`.
The ledger records 108 current activation decisions and is published in
`optima_eodhd_research.universe_admissions`. These are new explicit admission
dates, not invented dates for earlier legacy discovery collection.

## September 25 review and expansion

Universe **0.5.0** contains 502 retained company entries and 492 listings:
110 verified legal identities, 388 pending identities and four rejected legacy
placeholders. Of these, 108 qualify for detailed-tracking admission; the two
verified display companies do not qualify under the current sector evidence.
The admission evaluation leaves 394 entries for review, including rejected or
out-of-sector entries. These counts overlap sectors and are not 502 unique
verified investable companies.

- Added insitro, Agility Robotics, Lightmatter and Antora Energy as official-
  source-supported discovery candidates spanning all four sectors. Legal
  identity and ownership remain pending; do not call them verified private
  companies. The unlisted-candidate queue increased from 56 to 60.
- Verified Form Energy's current battery-sector membership from its official
  technology description; legal identity remains pending.
- Rejected display-panel-only semiconductor membership for Samsung Display and
  LG Display under the existing chip taxonomy. Their verified legal identities
  remain. Separately supported chip activities can be reconsidered.
- Corroborated and promoted HORIBA, Moderna, BioNTech, ASML and Lakefront
  Biotherapeutics against current GLEIF records. Retained stable company/listing
  IDs and earlier names as aliases; did not infer historical alias boundaries.
- Inspected every current identifier and alias structurally: no shared CIK/LEI
  collisions, but 29 cross-company alias collisions remain for adjudication.
- Refreshed 20 pending identifier checks with GLEIF/SEC. Recorded parent/subsidiary
  mismatches (Catalent and Merck), a NIO ADR/underlying mapping issue, an identifier
  name conflict, and renamed entities needing dated business/listing review.
  Successful registry retrieval does not automatically resolve these issues.

Sources are captured with checksums in S3; the capture manifest, review files,
policy and ledger accompany the immutable universe release. Primary business
sources include [insitro](https://www.insitro.com/platform/),
[Agility](https://www.agilityrobotics.com/company-overview),
[Lightmatter](https://lightmatter.co/), [Antora](https://www.antora.com/technology),
[Form Energy](https://formenergy.com/technology/battery-technology/),
[Samsung Display](https://global.samsungdisplay.com/overview) and
[LG Display](https://www.lgdisplay.com/eng/company/info/outline/vision).
These establish described business activity, not independent product validation.

Verification and lineage:
`reports/company-universe-v0.5-publication.json`,
`reports/company-admission-review.json`,
`reports/company-registry-adjudications.json`,
`reports/company-universe-v0.5-review.json`.

## Collection cutover

The shared daily SEC/regulatory/disclosure runner routes dates from September
25 to 0.5. Earlier daily epochs and historical windows retain their versions.
Separate market/news/patent/profile streams stay pinned to their current
configurations and unfinished checkpoints; no market listing was added.
Personnel archive records inherit the parent window's universe. Reviewed
universe publication is not a claim that every collector has already queried
every new company. See `reports/universe-cutover-2026-09-25.json`.

Remaining work: registry verification for pending identities, dated subsidiary/
receipt/name-change relationships, alias collisions, broader private-company
discovery and complete company-specific source coverage. Unresolved entries
remain discovery candidates rather than silently admitted model entities.
