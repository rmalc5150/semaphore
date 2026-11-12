# Repaired AADI / Whitehawk market windows

These queries are partition-bounded. The pinned symbol stays AADI.US; the actual requested ticker is in record_json.payload.provider_symbol.

## counts

```sql
SELECT window_id, json_extract_scalar(record_json, '$.payload.provider_symbol') AS provider_symbol, min(event_date), max(event_date), count(*) AS rows, count(DISTINCT event_date) AS dates FROM optima_market_research.market_prices_windows WHERE window_id IN ('345f05b5d1773549eb922c0cc299c94a570a0e2e5df289e63f7dbbbc517b3b44','8f813248ad3f9f4275facc7f53de2deb7df3be726d8aa5c9beedd961d2cc97ff','c6e0e38978b8f0a97ed83c49e407a5f541931e53a500d1dfd2739a43bf25a1fb','e264deb68a092360a8708a091a92c3453bc26082d7fd430302f120e587b2cba6') GROUP BY 1,2 ORDER BY 1,2;
```

## incorrect_boundary

```sql
SELECT count(*) FROM optima_market_research.market_prices_windows WHERE window_id IN ('345f05b5d1773549eb922c0cc299c94a570a0e2e5df289e63f7dbbbc517b3b44','8f813248ad3f9f4275facc7f53de2deb7df3be726d8aa5c9beedd961d2cc97ff','c6e0e38978b8f0a97ed83c49e407a5f541931e53a500d1dfd2739a43bf25a1fb','e264deb68a092360a8708a091a92c3453bc26082d7fd430302f120e587b2cba6') AND ((event_date < '2025-03-19' AND json_extract_scalar(record_json, '$.payload.provider_symbol') <> 'AADI.US') OR (event_date >= '2025-03-19' AND json_extract_scalar(record_json, '$.payload.provider_symbol') <> 'WHWK.US'));
```

## samples

```sql
SELECT * FROM optima_market_research.market_prices_windows WHERE window_id IN ('345f05b5d1773549eb922c0cc299c94a570a0e2e5df289e63f7dbbbc517b3b44','8f813248ad3f9f4275facc7f53de2deb7df3be726d8aa5c9beedd961d2cc97ff','c6e0e38978b8f0a97ed83c49e407a5f541931e53a500d1dfd2739a43bf25a1fb','e264deb68a092360a8708a091a92c3453bc26082d7fd430302f120e587b2cba6') ORDER BY rand() LIMIT 20;
```