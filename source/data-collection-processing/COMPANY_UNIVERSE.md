Latest review September 25: universe **0.5.0** is published and Athena-verified. See [COMPANY_ADMISSION.md](COMPANY_ADMISSION.md) for the current 502-company universe, 108 dated admissions, identity corrections, display decisions and preserved historical epochs. The 0.3 details below are retained as release history.

# Company universe version 0.3.0

Version 0.3.0 is published and query-verified in `optima_eodhd_research`, using
workgroup `optima-eodhd-research` in `us-east-1`. Local source:
`config/company-universe.v0.3.json`. Immutable release:

```text
s3://data-collection-059416028963-us-east-1-an/research-data/curated/company_universe/releases/3d32c2625a0b6ba513b5b7b0ca0dd0f68905a6546d07c6dc3e954ef2ab4d2736/
```

There are 498 retained company entries: 105 verified identities, 389 pending
identities, and four rejected receipt-derived placeholders. All 492 listing IDs
are preserved. Aliases increase to 665 and external identifiers to 988. Rejected
placeholders remain available for old observation references and are disabled
for new collection; they have not been merged into a legal entity.

Four new legal-company IDs are anchored to audited GLEIF records:

| Company | LEI | Collection decision |
| --- | --- | --- |
| LG Energy Solution | 988400QX6P286XA6ZS85 | Enabled; verified energy-storage/battery activity |
| Applied Materials | 41BNNE1AFPNAZELZ6K07 | Enabled; verified semiconductor equipment activity |
| Samsung Display | 9884004ARY4RODDUCT12 | Disabled; semiconductor-sector scope pending |
| LG Display | 988400P37K91W0SABO95 | Disabled; semiconductor-sector scope pending |

Intel reuses its existing verified company ID. Current registry legal names,
including Korean names, are retained alongside reviewed English/source aliases.
Alias and sector historical start dates remain unknown. Current legal identity
does not establish historical identity or patent title. Display manufacturing
is not automatically treated as chip manufacturing under the current taxonomy.

Four Applied Materials receipt listings keep their existing listing IDs but now
use the legal underlying company's ID in `company_id`, explicitly qualified by
`company_role='underlying_issuer'`. `depositary_issuer_name` distinguishes CIBC,
Bualuang and InnovestX from Applied Materials. Receipt types and listing/trading
dates are preserved, including the Cboe-to-TSX transition. The original company
placeholders and all old universe snapshots remain unchanged in previous releases.
Pending Brazilian and Mexican Applied Materials listings remain unresolved.

The schema adds optional listing-role, depositary-issuer and trading-start fields,
plus explicit depositary-receipt types. Old snapshots still validate. Evidence,
stable ID mappings and the promotion report are included in the S3 release.
`reports/patent-universe-promotion-2026-09-23.json` records the exact changes.

The existing daily timer is enabled and active. `collection_operations.py`
routes dates before September 24, 2026 through 0.2 and dates from September 24
through 0.3. Because the runner collects completed days, the first normal 0.3
window is September 24, collected on September 25 or a later catch-up run.
The cutover is configured and tested; no future 0.3 collection is claimed yet.

Old stream IDs, task checkpoints, progress origins and unfinished reconciliation
are retained. Reconciliation of closed epochs tapers off as dates leave the
requested lookback; explicitly pending dates continue to drain. Window limits
apply per source per epoch during the transition. Historical defaults, standalone
collector defaults and the long-running NMPA baseline remain pinned to 0.2.
For deliberate new 0.3 historical work use
`--config config/collection-operations.v0.3.json`, or pass
`--universe config/company-universe.v0.3.json` to collectors supporting that flag.
Do not change an unfinished cohort's universe merely to resume it.

Manual checks:

```sql
SELECT universe_version, review_status, collection_enabled, count(*)
FROM optima_eodhd_research.universe_companies
GROUP BY universe_version, review_status, collection_enabled;

SELECT l.exchange_mic, l.ticker, c.canonical_name AS underlying_company,
       l.security_type, l.company_role, l.depositary_issuer_name,
       l.valid_from, l.valid_to, l.trading_from
FROM optima_eodhd_research.universe_listings l
JOIN optima_eodhd_research.universe_companies c ON l.company_id=c.company_id
WHERE l.company_role='underlying_issuer';

-- Original memberships on retained placeholders remain historical evidence.
-- For the currently enabled research universe, filter the company as well.
SELECT s.sector_id, count(DISTINCT s.company_id)
FROM optima_eodhd_research.universe_sectors s
JOIN optima_eodhd_research.universe_companies c ON s.company_id=c.company_id
WHERE c.collection_enabled AND c.review_status <> 'rejected'
  AND s.review_status='verified'
GROUP BY s.sector_id;
```

Rebuild the exact reviewed release locally:

```bash
.venv-athena/bin/python patent_universe.py --prepare-athena
```

The stable ID registry is append-only for identity keys and rebuilds reuse the
same IDs. Existing versioned outputs must agree with the rebuilt data. Publication
uses `company_universe_athena.py publish`, followed by `deploy --update-existing`
with the prepared release directory. All seven tables are live; six SQL checks
passed. The private-company queue and EODHD coverage remain the original bounded
snapshots, not an assertion that subsequent profile cohorts have been reviewed.

## Archived version 0.2.0

SEC, clinical/regulatory and disclosure collectors used this universe before
the dated 0.3 daily cutover. Coordinated daily/historical operation is documented in
COLLECTION_OPERATIONS.md. Existing Athena pilots still retain their captured
universe versions; changing collector defaults does not rewrite old releases.

Version 0.2.0 is a validated research universe with stable UUIDs. It is stored
locally in `config/company-universe.v0.2.json` and published with its stable-ID
registry, registry checks, private-discovery queue and coverage report under:

```text
s3://data-collection-059416028963-us-east-1-an/research-data/curated/company_universe/releases/233005bc22883a72cc6e9754b7a81e9495f83b276904a201ea3e4b785880d016/
```

The Athena database is `optima_eodhd_research`; the workgroup is
`optima-eodhd-research`.

| Item | Count |
|---|---:|
| Company entities | 494 |
| Verified company identities | 101 |
| Pending company identities | 393 |
| Listings | 492 |
| Aliases | 655 |
| Former-name aliases | 149 |
| External identifiers | 984 |
| Verified sector memberships | 497 |
| Plausible unlisted-company candidates | 56 |

The following Athena tables are now advanced to the verified 0.3 release above:

- `universe_companies`
- `universe_sectors`
- `universe_listings`
- `universe_aliases`
- `universe_identifiers`
- `private_company_candidates`
- `universe_coverage`

Company IDs, listing IDs, alias IDs and identifier IDs are UUID4 values stored
in `config/company-id-registry.v1.json`. Later versions reuse this registry.
Listings sharing a corroborated CIK or LEI can map to one company; ISIN and
EODHD symbols attach to listings. ADR/GDR and other wrapper-like instruments
remain separate listings. Provider names and tickers cannot merge companies.

Sector support and legal identity are deliberately independent. A pending
company can have a verified current sector membership when the business
description supports the activity but the legal identity still lacks registry
corroboration. `valid_from=null` means the historical start is unknown; current
descriptions are never backdated. Former-name extraction records source evidence
but leaves unknown validity boundaries null.

The private-company process is a discovery queue, not a global private-company
directory. The bounded regulatory release produced 281 organization names: 56
plausible unlisted-company candidates, one listed-name match, 148 institutions
or non-company organizations, and 76 ambiguous names. Absence from the partial
EODHD cohort does not prove private ownership.

The enabled `optima-eodhd-profiles.timer` runs daily at 00:30 UTC with a random
delay, four workers, a maximum 7,900-profile cohort and a 5,000-call reserve.
At the current inventory size, approximately 17 additional quota days are
required. Raw profile collection is automatic; a new reviewed universe release
must still be prepared after additional cohorts because promotion is an
evidence-bearing decision.

Useful queries:

```sql
SELECT review_status, count(*)
FROM optima_eodhd_research.universe_companies
GROUP BY review_status;

SELECT sector_id, review_status, count(*)
FROM optima_eodhd_research.universe_sectors
GROUP BY sector_id, review_status
ORDER BY sector_id, review_status;

SELECT discovery_status, count(*)
FROM optima_eodhd_research.private_company_candidates
GROUP BY discovery_status;
```

CIK checks use the SEC company-ticker association file and LEI checks use the
GLEIF LEI-record API. Exact identifiers with materially different names remain
pending. The SEC notes that its ticker association file is updated periodically
and is not guaranteed complete, so it is corroborating evidence rather than a
complete global registry.
