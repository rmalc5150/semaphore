# November 7 targeted checkup

Current evidence: state.json and health.json, checked 10:05/10:00 UTC. Notification delivery errors empty. Market unresolved counts: 176 daily, 202 historical; 52 reviewed exclusions. Many incidents are shared-lock waits.

## Repairs

1. USDA: official portal https://apps.fas.usda.gov/opendataweb/home identifies api.fas.usda.gov. Old OpenData route returns 500; the current host with the former API_KEY header returns API_KEY_MISSING. Using the existing secret as api_key returns 200. The revised adapter emitted 1,875 unique rows for 2016 corn, exhausted pagination and omitted credentials from provenance. No key replacement is needed. See usda-adapter-live.json and usda-query-key-probe.json.
2. Personnel archive discovery: previous invocation scanned the entire checkpoint inventory before collecting up to eight windows, holding the supervisor lock for about two hours. Added bounded 200-key discovery, durable lexical scan cursor and pending manifest queue. Pending manifests survive restarts and are consumed only after processing or a durable processed/retry receipt. Failed/deferred work is revisited on subsequent inventory cycles; no claim of historical completeness is made. Live discovery: 200 keys, two pending manifests, 9.29 seconds (archive-discovery-live.json).

26 focused tests passed (tests.log), covering cursor progression, pending recovery, USDA migration and existing adapter validation. Deployment succeeded for three modules across 149 historical workspaces; root controller and daily copies also updated. See deployment-result.json. No services were stopped, locks removed, messages sent or permissions broadened.

Production USDA publication and the next complete people run remain unverified. The earlier people run completed successfully before this repair, with checkpoint verification and publication results, so it is not evidence of the new scan's full-run performance. Existing unrelated source failures remain open.

Owner actions are the three Athena payload spot checks in [the status document](../../../data-source-status-2026-10-26.md). Earlier USDA support instructions are withdrawn: the issue was collector host/authentication configuration.
