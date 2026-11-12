# November 5 email repairs

Reviewed the supplied 11:05 CET overview, sampled a representative receipt for each historical source present, and compared current journals/checkpoints. The email covers 14 service groups and 55 historical scope groups. The 3,933-item historical handoff remains dated October 30; it is not a fresh failure count.

## Completed changes

- Notification delivery is recovered: latest notification errors empty, CloudWatch delivery alarm OK, and owner confirmed receiving the email. Earlier subject-length repair remains deployed.
- Search policy now references its actual enabled weekly timer. Weekly age thresholds are eight days. For a service never started during the current boot, timer activation provides scheduling grace only; it does not constitute data progress.
- Daily conference monitoring no longer uses the migrated historical checkpoint. Its current daily cursor reached November 5 and its referenced manifest is exhausted/complete. A separately evidenced scope-completion marker allows an obsolete stall to recover without hiding source failures.
- HKEX changed-prefix/changed-total failures get a new immutable collection run after a six-hour cooldown, rather than repeatedly resuming the invalid prefix. Previously captured artifacts/manifests remain retained. Downstream prerequisite gates remain. Deployment: 149 historical workspace copies plus 16 daily workspace copies; root controller code updated. Live replay and downstream publication are not yet verified.
- USGS archive support uses 19 exact links discovered on official mineral pages. URL identity is allowed only by the reviewed mapping; untrusted hosts cannot be promoted. Previous-edition comparisons resolve through the same mapping. Three modules deployed across 149 historical workspaces and the daily workspaces.

## Verification

83 focused tests passed (`tests-final.log`). A broader initial run encountered a missing target for the existing `company-universe.v0.2.json` fixture; the new test's conditional-write setup was corrected before the final run. The unrelated fixture-dependent test is not represented as passing.

Four official 2016 USGS PDFs downloaded with validated signatures, checksums and report identities. Parser counts: lithium 67, cobalt 105, nickel 128, graphite 88 statistics. Lithium contains unresolved cells; graphite contains unresolved units/row grouping. These remain explicit review flags, not certified values. Downloads are local probes; production publication is not claimed.

Relevant receipts:
- `receipts.json`, `email-scope-counts.json`: sampled historical failures and scope grouping.
- `conference-progress.json`, `health-after.json`, `selected-verification.json`: live monitoring checks.
- `usgs-link-provenance.json`: official index-to-download links.
- `usgs-probes.json`: size, checksum, parsing results and retained gaps.
- `deployment-result.json`, `usgs-deployment-result.json`, `monitoring-deployment.json`: successful deployments.
- `provider-retests.json`: USDA request still HTTP 500.

No test messages were sent, permissions broadened, pauses reversed, or source gaps marked complete without evidence. Shared locks and memory limits remain intact. Captured data is not considered fully available until its publication and Athena query are verified.

## Owner actions / remaining work

See [today's streamlined list](../../../data-source-status-2026-10-26.md). Owner action: ask USDA FAS support about the exact authenticated failing route, and continue the selected Athena payload checks. Census activation and Copernicus licence acceptance are resolved; do not ask for replacements again.

Remaining engineering work includes publication queue latency, actual HKEX replay, duplicate patent/preprint identities, market coverage, historical credential-recovery replay, TED/BLS artifact failures and other retained source-specific failures. These remain open, not transferred to the owner as credential-shopping tasks.
