# Post-upgrade backlog work — October 21

## Verified configuration

The machine is now t3.large with approximately 7.6 GiB usable RAM. The maintenance marker is absent. Effective shared MemoryHigh/Max are 5/6 GiB; authenticated and publication worker MemoryHigh/Max are 4/5 GiB. No services were marked failed at the final check. This does not clear retained source-scope failures.

## Changes applied

- Research publication: increased from 2 to **8 windows per source group per invocation**.
- Specialist publication: increased from 24 to **48 windows per invocation**.
- Deployed separate `zz-publication-batch.conf` service overrides; their exact bodies are saved alongside this report. Global locks, memory caps, provider budgets and Athena verification remain intact. Existing running invocations are not interrupted; updated commands apply on new invocation.
- Monitoring now treats `partial` outcomes with `record_limit` or `page_budget` as bounded continuation, matching the collectors' committed-cursor semantics. Failed outcomes with those reasons, upstream result caps and stalled progress still alert.
- Refreshed health monitoring and saved `backlog-baseline.json` for subsequent comparison.

Validation: 47 tests passed across collection alerts, health repairs, window publication, research publication and overview formatting. Effective systemd commands confirm the new batch sizes and 5 GiB worker caps.

## Live source recovery

At **19:22 Madrid time**, HKEX verified the previously blocked January 3, 2021 window: **30 filings, 6,846,673 original-document bytes**. It then advanced to January 4, committed another bounded partial page and successfully checkpointed runtime state to S3 at **19:24 Madrid time**. The workbook parser repair is therefore making production progress. Fresh Athena publication for that particular window has not yet been verified in this session.

## Unresolved

- EIA September 2026 generator workbook: the official indexed archive URL returns HTTP 200 HTML rather than XLSX. The same-month nonarchive route also returns HTML. Do not reinterpret that response as an empty inventory or substitute a different month. Source validation remains enabled.
- Historical date gaps, market coverage, provider 400/403 responses and other retained scope failures still need individual resolution.
- Larger publication batches are scheduled, but a sustained reduction in queue depth is not yet demonstrated. Compare future queue snapshots and completed receipt rates with the saved baseline; larger batches can also increase the time other workers wait for the shared lock.
- No post-upgrade OOM occurred during this observation period. That is not yet proof that the original high-memory scope has completed.

## User actions

No additional configuration or purchase is required now. Keep the instance running and continue optional Athena data-quality checks. The existing timers continue the bounded collection/publication work. Do not treat this report as confirmation that the entire backlog or every pipeline is repaired.
