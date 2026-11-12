# Athena checks for repaired sources

Region `us-east-1`; workgroup `optima-specialist-inputs`. These samples inspect known verified scopes, not random archive coverage.

## assignments — verified 1 records in this scope

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '891cce06a194c91886128906f0f04ff421498e53d640b36d133465a84961c129'
LIMIT 20;
```

## caiso — verified 120 records in this scope

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '4b491e015c26301f0ff3097368306e0197cc3cd6dc2433cccadf08b6bbf91609'
LIMIT 20;
```

## mlperf — verified 2 records in this scope

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '11fc7b4cd60851ead8a9c3c295aa8b6ba3d0cb35f6984b9bcd857b65f2b143f0'
LIMIT 20;
```

## pmc — verified 1 records in this scope

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '2e40cd368e73f89ad3144e1ca20a90898521f27bc6be541f40ba50da57e91379'
LIMIT 20;
```

## sam — verified 143 records in this scope

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '6f892603fd4e1330daabc25e70825d96b09973ea7c7d61c7e95c93db18e0c43a'
LIMIT 20;
```

## eia-generators — verified 1826 records in this scope

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '5b088153420b49d5c8a490ab6e9b690bff487f68a05ca0cabd728e7664e6c913'
LIMIT 20;
```

## Newly repaired scopes

### assignments-01

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '6fa1487c82947bb8bcae1d37b9ab26edf610db687108ba454ad01147e8411f00'
LIMIT 20;
```

### assignments-02

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '44765d4c333de696ffb2a352a12d32aaad97ceaca648ff100db4ac45635f185e'
LIMIT 20;
```

### assignments-03

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '1ea2a39ae98dfe25a1d618e553f67f1138872ec489250eae3f631f05ddf62483'
LIMIT 20;
```

### assignments-04

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '27fdd2a9f054f362154803074b225d9e53a306274ffb5334d28860018e5b9a7a'
LIMIT 20;
```

### pmc-01

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '20717cec234c727703c5c4cc7db8760b343d26b2f377fc75ada8f3372beeb89e'
LIMIT 20;
```

### pmc-02

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '0c6a917262618df1ad5c8cd722a2f9c831c5804d5f361748bbd2a3e380591b1e'
LIMIT 20;
```

## MLPerf — actual benchmark artifact content

Use workgroup `optima-collected-data`. This is the tested content filter; `LIMIT` alone does not guarantee a scan ceiling.

```sql
SELECT *
FROM optima_collected_data.observations
WHERE source = 'mlperf_results'
  AND dataset = 'specialist_inputs'
  AND json_extract_scalar(record_json, '$.payload.data.artifact_kind') = 'original benchmark configuration or log'
LIMIT 1;
```
