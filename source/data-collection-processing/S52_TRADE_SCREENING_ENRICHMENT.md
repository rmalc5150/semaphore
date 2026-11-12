# S52 — authority evidence, company matching and product exposure

Implemented on 2026-10-18 in `trade_screening_daily.py` and `trade_screening_enrichment.py` (`trade-screening-evidence-v1`). The original `trade_screening` snapshot remains available. The daily worker produces `trade_screening_enriched / specialist_inputs` after an exhausted, complete original capture, queues it for the existing Athena publisher, and rereads the live RDS directory once per new daily snapshot. Matching is read-only against RDS; no registry records or production events are created.

## Evidence retrieval

- Archive the original CSL capture and link each enrichment to its parent observation, record and manifest. Preserve provider ID and list identity. Raw collector and enrichment identities now include the list as well as the provider ID: the initial 26,154-row snapshot has only 26,058 unique bare IDs but 26,154 unique list/ID combinations. Old saved records retain their original identities; new captures use the corrected key.
- Retrieve Treasury's official SDN.XML and CONSOLIDATED.XML structured exports. Preserve raw response bytes in `source_documents/trade_screening_documents/{sha256}`, and retain each original entry XML, fields with paths, entry UID and evidence reference. Verify UID, name, entity type and reported programs against the CSL entry before labeling the authority entry verified.
- Retrieve the source-list and source-information URLs reported by each CSL authority. Preserve readable HTML paragraphs or PDF pages. A name appearing in a general page is an entry candidate, not a verified entry. Unresolved/non-machine-readable authority pages stay explicit gaps.
- Retrieve explicitly linked Federal Register notice URLs, plus the ten most recent notice links on OFAC's current sanctions-list updates page. Archive the original notices and retain their dates, paragraphs and entry references. An exact OFAC entry link is recorded as an authority reference; name occurrences remain notice candidates. Neither automatically determines whether a notice added, amended or removed the entry.
- HTTPS official-host allowlisting and redirect checks apply. Treasury's precise public GovCloud S3 export bucket is allowed only when reached from its official export service. Do not persist signed redirect query strings. XML parsing disables external entity resolution and network access.

The notice search is bounded current coverage, not a reconstruction of historical designation notices. Missing historic notices, blocked authority sites and unresolved list entries are reported in `gaps` / `resource_gaps`. The current State nonproliferation page returned HTTP 403, and the DDTC page exhausted HTTP-client retries during launch. These gaps do not become successful evidence claims. A later daily capture retries retrieval; pending transient requests resume from durable checkpoints.

## Identity and relationship normalization

`payload.data.enrichment.identity` preserves source list, entry ID, entity type, names, aliases, addresses, typed identifiers and their CSL field paths. It separates aircraft operators, vessel-owner assertions and “Linked To” statements into source-reported relationships. Aircraft manufacture dates stay typed identifiers, not event dates. Original authority entry XML retains the unflattened grouping of identifiers and addresses.

EP-MOG / UID 15477 identifies an aircraft. MSN 3165, model B.146-300 and operator MAHAN AIR have separate meanings. The operator is not automatically the owner or manufacturer, and the model mention does not apply the restriction to every aircraft of that model.

## Company matching

Read companies, aliases, reviewed identifiers, products and product-company relationships in one TLS-protected, read-only RDS transaction. Freeze and archive the directory snapshot/hash for reproducibility. Exclude archived or rejected companies. Names and aliases are candidates only; aircraft/vessel/person names are not treated as company names. Operators and linked parties produce separate company-match candidates.

An existing, reviewed RDS identifier in namespace `trade_screening_entry` can verify a listed company's identity. Its value must be the exact CSL source-list label, a vertical bar, and the authority entry ID, for example:

`Specially Designated Nationals (SDN) - Treasury Department|12345`

Both company and identifier must be verified. Multiple companies asserting the same identity are downgraded to conflicting candidates. Creating/reviewing these directory assertions is a separate registry process; this worker never inserts them automatically. Name-only operator matches are not promoted through the aircraft's UID.

At launch, the live RDS directory contained zero companies, products and relationships. Consequently, real outputs are `unmatched_directory_empty`; no matches or product exposures are fabricated. Future complete daily captures reread the directory and re-evaluate the entries.

## Product exposure

Use verified, unarchived products and reviewed product-company relationships with evidence. Preserve relationship role, territory, validity dates and observed-at date. Assess validity on the current assessment date; expired relationships remain historical context. A name-only company match can produce a clearly labeled exposure candidate, never a confirmed affected product or legal restriction.

Existing RDS relationship roles cover developer, owner, manufacturer, licensee and commercial partner. The schema does not yet directly model customer, supplier, distributor or operator relationships. Those exposure paths require a future evidence-backed relationship extension; this worker does not invent them. Legal applicability, actual sales/supply impact and event-date historical relationships remain undetermined.

## Operation and inspection

`optima-trade-screening-enrichment.timer` probes every five minutes. It acts only after complete daily S52 capture and resumes unfinished work between probes. `--bootstrap` permits the latest complete saved snapshot for the initial deployment; it does not establish historical sanctions status or trigger an email. No historical sanctions backfill is claimed.

The worker archives authority resources once per snapshot, retries transient failures with a 30-minute delay and records terminal failures as gaps. Each output task covers at most 500 input rows; the default invocation processes four tasks. SQLite checkpoints are in `reports/trade-screening-enrichment.sqlite3`; the local and S3 status receipts are `reports/trade-screening-enrichment-latest.json` and `operations/trade-screening-enrichment/status.json`. Publication entries use the existing specialist queue. An output being captured/queued does not establish that Athena publication has completed.

```sql
SELECT provider_id, ingested_at,
       json_extract_scalar(payload_json, '$.data.name') AS name,
       json_extract(payload_json, '$.data.enrichment') AS enrichment
FROM optima_collected_data.observations
WHERE source = 'trade_screening_enriched'
  AND dataset = 'specialist_inputs'
ORDER BY ingested_at DESC
LIMIT 20;
```

See [event integration](ENTITY_DISCOVERY_ROLLOUT_PLAN.md#event-pipeline) for required event deduplication, baseline, date, identity, removal-verification and exposure-assessment rules. Production event emission is deliberately a separate implementation item.
