# Service repairs — November 20, 2026

The attached email was dated **November 19, 15:35 CET**. It listed 16 service groups plus separate historical scopes. This pass addresses the service failures; it does not certify the historical backlog complete.

## Real failures diagnosed and repaired in code

### Regulatory publisher: scan cursor denied

The November 18 scan patch installed successfully, but its cursor write failed at:

`research-data/operations/regulatory/publication-scan.json`

That path was outside the production worker's allowed write resources. This was a defect in the earlier change. Other owner groups continued to publish; the regulatory group's final status was failed.

The cursor now uses:

`research-data/operations/regulatory/publication-retries/_scan-cursor.json`

The existing publisher policy permits GetObject/PutObject under `operations/*/publication-retries/*`; no IAM expansion is proposed. The cursor remains distinct from window retry receipts and is not a publication receipt. Its 128-candidate rotation, checksum validation and conditional writes are unchanged. The controller cannot call IAM policy simulation, so an actual worker-role conditional write/read probe is included in deployment. Permission success has **not yet been asserted live**.

### Patent daily capture: minimum split size prevented further recovery

The exact incomplete day is **November 10**, partition hour **04**. Its parent manifest has **30,939 committed records**. The failing child covers **04:00:00–04:03:45**, contains **3,000 committed records**, and reports `source_changed_refresh_required`. These numbers refer to parent and child manifests, not an additive total.

Adaptive subdivision stopped below five minutes, leaving this busy 3-minute-45-second range repeatedly restarting. Recovery can now subdivide as far as a one-second threshold. Completed hours and completed child ranges remain committed; old attempts are retained. Page/request budgets, strict counts, date bounds, identities and full-day completion requirements remain unchanged. A changing source that remains inconsistent is still incomplete; no exclusion or fabricated completion was added.

A regression exercises repeated changes below the previous five-minute floor and checks that all records are eventually retained when the source settles.

## Monitoring corrections applied live

- During scheduled sleep, worker monotonic timestamps now map back to the correct historical wall-clock time. Monitoring can recognise a completed, successful invocation **with verified output**, without pretending the sleeping worker was freshly inspected. Empty successful invocations alone still cannot close a failure.
- CMS catalog and FDA review publishers are now checked against their **own queued windows**, rather than missing evidence or an unrelated whole-specialist backlog. Each check requires matching window IDs and manifest lists, a verified receipt and a matching verification checksum/identity. CMS has ten queued windows and FDA review has 168 at inspection. Missing/mismatched receipts remain pending. These are bounded checks, not source-wide completeness claims.
- Normal batch sleep and explicit raw-validation/owner pauses were preserved. Source failures and unreviewed price gaps were not waived.

The final live refresh reduced active service groups **16 → 8**, with **zero inspection errors**. CMS catalog and FDA review process alerts cleared only after all ten CMS windows and all 168 FDA review windows matched newer verified publication receipts. See `health-refresh-scoped.log` / `health-after.json`. Earlier signal incidents without adequate recovery evidence remain retained.

## Deployment and next verification

**Worker changes are staged, not yet live-verified.** M7 is deliberately stopped under the existing batch policy. The active controller timer `optima-service-repair-install-20261120.timer` checks every five minutes, waits for a normal worker boot and SSM availability, then applies only the two publication runtimes and the active patent capture runtime. It preserves backups, checks exact anchors, compiles before replacing files, preserves ownership, and performs the cursor permission probe. It stops after success, failure or 25 hours. No worker wake, IAM change or extra instance session was requested.

- Controller deployment state: `publication-deployment-state.json`.
- Worker deployment receipt: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/repairs/2026-11-20/deployment-result.json`.
- After installation, verify cursor advancement, a successful regulatory publication receipt/readback, and the patent partition's next committed progress. These checks remain necessary before closing the two real failures.

The current sleep began **03:57 CET November 20**. Earliest threshold-based wake: **17:57 CET November 20**. Maximum-off deadline for pending work: **03:57 CET November 21**. The earlier wake depends on the existing queue threshold. There are **30 durable service requests** waiting. These are policy bounds, not completion promises.

## Remaining work and owner actions

No new API key, licence purchase, IAM change, manual service restart or owner exception is requested by these findings. Existing Athena field reviews can continue.

Remaining engineering work includes pending deployment/live verification above, CMS/Crossref publication backlogs, prior assignment/NIST execution failures still lacking enough recovery evidence, retained authenticated-source 429s, and market coverage gaps (**174 daily / 201 historical symbols; 56 reviewed exclusions** at last inspection). Do not blanket-exclude missing prices or treat source success as proof that every historical period is available in Athena.

EDINET 2016 remains excluded. Reddit, Bluesky, GitHub source capture and Marketaux remain paused. SMS remains working. Historical gap review is separate from the service repairs in this pass.

## Evidence and tests

`worker-before.json` contains the exact AccessDenied publisher result and patent outcome. `patent-parent.json` / `patent-child.json` retain the exact manifests and task bounds. `cursor-policy-simulation.json` records the unavailable simulation, not permission success. The known existing policy scope is in `constellation/migration/m7-research-publication-policy.json`; the real permission probe remains pending.

**123 regression tests passed**, covering publication continuation, patent recovery/budgets, snapshot-clock translation, prior verified invocation recovery, scoped receipt mismatch rejection and the other monitoring behaviours. See `tests.log`. Health/incident refreshes recorded state with notifications disabled; no manual email/SMS was sent.
