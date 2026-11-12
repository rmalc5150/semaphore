# HKEX original-document repair and pipeline resume — November 9, 2026

## Outcome

HKEX metadata is enabled again, with zero consecutive raw failures. All four previously failed batches were replayed successfully using normal per-source locks and fenced leases, then published through staging/count checks into `optima_metadata_engine.source_observations`.

Athena verified **86 raw-complete row occurrences / 53 distinct filing IDs** across the four batches. These batches overlap; neither figure proves complete historical coverage. Query `063ba399-87f9-4036-a6f1-0f73b3922f4a`.

Payload inspection confirmed Chinese originals retain their own NEWS_ID, `zh-Hant` language, original PDF checksums/URLs and native Chinese listing provenance. Query `462996a2-ecce-4b56-a203-d7e8715c1b7b`. The three English notice IDs returned **zero** substantive filing rows: query `c4e40e4b-1d04-4089-aecf-6933cbf314c7`.

## Cause and repair

The failing English URL was a short language-availability notice, not an issuer filing. The official Chinese daily listing exposed separate announcement IDs. The repair archives every candidate matching the exact issuer and release minute as an independent Chinese original; it explicitly does not assert exact translation equivalence. English notices remain preserved as notices and evidence, not raw-complete substantive filings. This does not establish that an English version never existed or full coverage of Chinese announcements.

Older metadata-only batches now retrieve the exact original URL from the saved official listing. Native PDF/Office/HTML validation rejects placeholders, access blocks, unsupported content and incomplete originals. Immutable resolution receipts and cached source bytes are checksum-verified on reuse. Provider requests, batch time, memory and CPU remain bounded.

Code: `hkex_originals.py`, `disclosure_collection.py`, `metadata_engine/hkex_documents.py`, `metadata_engine/evidence.py`, `metadata_engine/worker.py`. Runtime packaging includes the new helper. Collector deployment updated 298 files across 149 historical workspace roots, plus local daily copies. Metadata deployment completed successfully after waiting for an idle worker. **46 focused tests passed.**

The publisher accepts an optional source filter for bounded repair publication; ordinary scheduled publication retains its existing behavior and five-batch bound.

## Resume checks

- Restored and verified 33 existing daily capture/publication timers; company-catalogue and product-search schedules included.
- Controller public API/archive/raw daily timers and historical dispatch are active.
- Daily and historical collection controls both permit work.
- All 15 historical workers are active: 5 native, 6 legacy, 4 public.
- Metadata worker timer is enabled/active; metadata controller timer active. Fresh accepted jobs followed deployment (including SEC, EIA and USGS).
- Owner pauses for Reddit, Bluesky, GitHub and Marketaux retained; access-layer entries unchanged.
- Final source states: 70 enabled, 78 raw-stopped, 5 owner-paused, 4 access-layer. Unrepaired raw-content holds are not waived.
- General metadata publication backlog: 2,066 accepted batches at 15:49 UTC. The four HKEX repairs are published; this backlog remains engineering work.
- HKEX has 61 queued jobs, including continued slices, at this snapshot. They remain under normal scheduling and validation.
- The controller's only failed systemd unit was the separate `ec2-code-backup.service`; this is not a collection/metadata failure.

## Your check

No access or credential action is needed. Run the HKEX aggregate in the verification schedule, then inspect the labelled payload and original-document links. This bounded sample query prunes to the four verified job partitions:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'hkex_news'
  AND job_id IN (
    '46593ba8eea0a120c8c8491dd86108fca59ffb6ae750d6fe84fb1296b9e3f64d',
    '6f092c5da838e805b5d6cd6d83d3986049fd573a13e936f0d6960de2e949b9ee',
    '9290e6e37ae98135a9ba0e0e677d93079044ef47fe7e7231c4f99879aed5a650',
    'eb80c4084859bd82ffd4ee27ed0d51716aea27113e8bba79212edc67d30b9112'
  )
ORDER BY rand()
LIMIT 20;
```

The review checkbox remains unchecked pending your inspection. Later batches and downstream dependencies are separate verification work.

## Evidence

`failed-batch-validation.json`, `tests-final.log`, `collector-deployment-result.json`, `metadata-deployment-result.json`, `before-resume.json`, `verified-replay-result.json`, `publication.json`, `athena-verification.json`, `payload-inspection.json`, `controller-timers.txt`, `worker-status-result.json`, `final-status.json`.
