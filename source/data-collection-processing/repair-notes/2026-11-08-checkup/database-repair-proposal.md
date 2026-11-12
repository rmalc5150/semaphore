# Database repair awaiting explicit approval — November 8

Observed: historical dispatch SELECTs exceed the client's 30-second timeout and remain executing on RDS. EXPLAIN estimates 24,396 rows plus sorting. A separate metadata worker source-selection SELECT ran for over 70 minutes and held 145 row locks before claiming a job. Online index creation failed with a five-second metadata-lock timeout. No query has been canceled and no index has been created.

Proposed controlled repair:
1. Re-read the live process list. Save IDs, users, durations and exact SQL.
2. Cancel only constellation_controller queries older than 30 seconds whose exact SQL begins `SELECT spec_json,result_json FROM backfill_jobs WHERE source_key=`; also cancel the metadata_engine_worker source-selection SELECT only if still older than one hour, with the exact query shape in database-active-queries.json. Do not terminate provider-capture processes or other SQL.
3. Use `mysql.rds_kill_query` for those current query IDs. The interrupted dispatcher/claim may retry. Do not delete queue rows or captured objects.
4. Add `source_status_updated(source_key,status,updated_at)` to constellation_operations.backfill_jobs using ALGORITHM=INPLACE, LOCK=NONE and a five-second metadata-lock wait. Abort if online operation is unavailable or locks remain.
5. Add a ten-second server-side time limit to dispatcher SELECTs, preserving current exceptions and retry policy. Update the schema definition for future installs.
6. Verify the index/query plan and bounded dispatch for USDA and Census. Capture and Athena publication require separate proof; queueing alone will not close source gaps.

Evidence: queue-schema-before.json, queue-query-plan.json, database-active-queries.json, database-locks.json in this folder.

Risk: cancelling a query interrupts its current scheduling/claim attempt, which must retry. It does not delete source records. The online index uses temporary database resources. Automatic approval review requires explicit approval before the live cancellation/repair sequence.
