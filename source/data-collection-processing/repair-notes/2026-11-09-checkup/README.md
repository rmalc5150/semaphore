# November 9 collection checkup

Reviewed the supplied email, current monitoring, representative immutable historical receipts, journals and bounded live source tests. This is a targeted repair record, not a complete historical/raw-content audit.

## Completed repairs

- **HKEX:** added a complete daily index snapshot before original-document capture. Subsequent bounded pages read that saved index and verify its checksum/provenance instead of re-querying a changing cumulative prefix. A new scoped contract preserves older runs; old failed cumulative-index runs can migrate immediately while newer failures retain cooldown. The live September 23, 2026 index returned all 890 entries with explicit provider exhaustion. Index validation does not establish that all 890 linked documents have been downloaded. The normal daily collector was started for the deployed repair and may wait for the shared lock.
- **Zenodo:** trim valid scalar publication dates before emitting the envelope; retain the unmodified provider date in payload. Date intervals/invalid values produce no invented scalar event date and carry an explicit source-date status. The historical route ran, but its provider HTTP 500 cooldown correctly prevented more requests; normal retries remain intact. New production commits for the specific repaired date formats remain unverified.
- **BLS:** owner explicitly approved the exact bls-policy-proposed.json after automatic approval review rejected a persistent IAM expansion. Added only GetObject/PutObject for the worker role under bls-labor/joins-cache, observed and versions. Existing policy statements and denies remain. Worker Put/Get probes passed for all three folders. Six saved AccessDenied scopes became eligible for bounded replay; original scheduler metadata was backed up. Subsequent live inspection found all six complete with exhausted committed manifests, totaling 70 observations. See bls-repaired-scope-verification.json. Their Athena publication/readback remains unverified. Provider retry limits were not reset.
- **USDA Athena:** exact November 8 cotton batch queried successfully: 1,500 rows / 1,500 distinct observation IDs, matching its committed manifest. Query ID `36c69eb3-dbe4-4eb8-9f67-85d27063a0d7`, 3,020,574 bytes scanned. This verifies that batch only.
- **Deployment:** four modules updated across 149 historical workspace roots (596 files), plus controller/daily copies, with backups and checksum/compile verification. See deployment-result.json.
- **Tests:** 46 targeted tests passed. An initial broader run also encountered the pre-existing missing company-universe.v0.2.json runtime fixture; it was not counted as passing.

## USPTO document access — superseded by owner exception

The owner subsequently explicitly instructed us to skip document `MMOWZII4X158X88` in application `35526479`. The exact exception is configured, schema-validated and verified against the saved provider row without calling the provider. The original failure is archived. Other documents in the same application are not excluded. The earlier support instructions are withdrawn.

See [exception deployment and verification](../2026-11-09-uspto-document-exception/README.md). This does not establish PDF capture or complete window/Athena publication.

## Still open — implementation work

Shared-lock/publication queue waits, full HKEX document/dependency recovery, patent office-action window recovery, TED exact S3 denial, market mappings (email: 175 daily / 202 historical unresolved, 52 reviewed exclusions) and the remaining historical pagination/access/content failures. The email's 236 gaps over five days include older evidence; the 3,933-failure handoff is dated evidence, not a new failure count today.

Saved data and successful dispatch are not full pipeline completion. Newly repaired scopes still need committed-data and Athena checks as indicated above. No new API subscription or purchase requirement was established.
