# Repaired-source Athena payload checks

Use region `us-east-1`, workgroup `optima-collected-data`. Run one statement at a time. These small samples are not random or completeness checks. `LIMIT` does not guarantee a scan ceiling; avoid `ORDER BY rand()` across the full archive.

## MHRA — published observations

```sql
SELECT *
FROM optima_collected_data.observations
WHERE source = 'uk_mhra'
  AND dataset = 'research_records'
LIMIT 5;
```

## CTIS — published observations

```sql
SELECT *
FROM optima_collected_data.observations
WHERE source = 'ema_ctis'
  AND dataset = 'research_records'
LIMIT 5;
```

## NMPA — published observations

```sql
SELECT *
FROM optima_collected_data.observations
WHERE source = 'nmpa_trials'
  AND dataset = 'registry_inventory'
LIMIT 5;
```

## EDINET — published observations

```sql
SELECT *
FROM optima_collected_data.observations
WHERE source = 'edinet_filings'
  AND dataset = 'specialist_inputs'
LIMIT 5;
```

## TED — published observations

```sql
SELECT *
FROM optima_collected_data.observations
WHERE source = 'ted_notices'
  AND dataset = 'specialist_inputs'
LIMIT 5;
```

## NMPA — detailed trials and dated events

```sql
SELECT *
FROM optima_collected_data.observations
WHERE source = 'nmpa_trials'
  AND dataset = 'research_records'
LIMIT 3;
```

## Exact repaired EDINET and TED payloads

The observations samples may return older metadata-only records or arbitrary content chunks. These tested queries use existing bounded verification partitions for the exact repaired files. The same files were confirmed in the live publication manifests.

### edinet_filings

```sql
SELECT *
FROM optima_collected_data.batch_verification_records
WHERE source='edinet_filings' AND dataset='specialist_inputs' AND batch_group IN ('2e233e16811f412ee3260f90ec4d8959bb9ad9be94e204b57a0aa639dab149ee','1663ed88f1caae2467cb131681e05d981edbc347dea9e757202bbf492aa90ca5') AND "$path" IN ('s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=edinet_filings/dataset=specialist_inputs/ingestion_date=2026-10-21/run_id=run_be813688-99ab-4fb0-ad7b-c484e16de0e3/page-00000001-part-00000-2d76e9be9458c9ac2134af2d5b9676710ab2d580a4c7ea04751aae0df51e0529.jsonl','s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=edinet_filings/dataset=specialist_inputs/ingestion_date=2026-10-17/run_id=run_f15f9378-3c5f-4e88-a277-8421e624a855/page-00000000-part-00000-02e6154818cc718f5fee218dcf65c8722d2a25b993abc4405e2a6a7ce9417b5c.jsonl')
LIMIT 8;
```

### ted_notices

```sql
SELECT *
FROM optima_collected_data.batch_verification_records
WHERE source='ted_notices' AND dataset='specialist_inputs' AND batch_group IN ('2a9acc653e20e88859c98299e846961681786eec99428265353c269e3f080534') AND "$path" IN ('s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ted_notices/dataset=specialist_inputs/ingestion_date=2026-10-21/run_id=run_80a4c8be-8750-4a45-9cf4-e74e9b22658e/page-00000006-part-00013-b54181c71efa4f0869e7e724055618e26738bd8c12d028a0ac7853017d36e946.jsonl','s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ted_notices/dataset=specialist_inputs/ingestion_date=2026-10-21/run_id=run_80a4c8be-8750-4a45-9cf4-e74e9b22658e/page-00000006-part-00014-3822c22f3850227f7b5b8d011690a773a418f8fcd3ee829211b2eabf2155862e.jsonl','s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ted_notices/dataset=specialist_inputs/ingestion_date=2026-10-21/run_id=run_80a4c8be-8750-4a45-9cf4-e74e9b22658e/page-00000006-part-00015-376e6878b313001392216e13a30bf67aa1d3d896e1fa53728d8941f1e1097ac3.jsonl')
LIMIT 8;
```

For TED notice `709615-2026`, all 89 chunks were retrieved and reconstructed during this audit; see `ted-reassembly-check.json`. A single chunk is not a complete notice. For EDINET, extracted document content is referenced under `payload.documents[].extraction.source_evidence`, with S3 keys relative to `research-data/`.
