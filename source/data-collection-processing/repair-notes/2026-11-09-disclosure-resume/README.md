# Disclosure pipeline restart — November 9, 2026

## Verified outcome

Daily capture completed the previously stalled October 16 window and advanced to October 17. It produced five documents, five passage-supported candidates, 1,861,137 text characters and 3,269 chunks. Canonical publication of all five derived stage windows passed Athena count verification, including the empty licensing-agreement window.

Fresh Athena aggregates:

| Route | Rows | Latest ingestion | Query |
|---|---:|---|---|
| disclosure_documents | 538 (288 distinct record IDs) | November 9, 16:05:59 UTC | `869f71ef-f472-4fe5-94c7-354fb6d5f875` |
| disclosure_candidates | 926 across four categories | November 9, 16:06:36 UTC overall | `31d37081-537f-4666-8133-ae9891de3b6c` |

New candidates: one press release, two M&A and two strategic transactions. Licensing agreements had no matches in this day; a verified empty capture does not refresh the last nonempty observation timestamp.

Historical capture completed January 1, 2016 and advanced to January 2. That date's empty observations do not prove subsequent historical coverage. Daily and historical backlog completion is not claimed.

## Causes and changes

The existing S11 daily chain was still blocked at a partial HKEX stage on October 16. Its controller process waited in the shared runtime queue. Earlier startup logs also showed a missing runtime universe file before the supervisor repair. The historical legacy route was disabled and had never progressed through the target range.

Installed isolated worker capture services on `i-06241bd1c4e91c2fc`:

- `optima-disclosure-daily.timer`: repeat 120 seconds after completion;
- `optima-disclosure-historical.timer`: repeat 300 seconds after completion;
- local disclosure-only nonblocking lock serializes both, preserving provider fairness;
- 512 MiB memory maximum, 25% CPU, 15-minute invocation timeout;
- one completed source-calendar day per invocation; bounded HKEX pages and document records resume;
- existing frozen v0.5 universe is loaded from its checksummed S3 snapshot, with no fixture substitution;
- existing daily task identity/cursor preserved; historical target remains January 1, 2016 through October 14, 2026, then daily covers October 15 onward;
- disabled old controller S11 daily timer and removed it from `constellation.resume_daily.DAILY_NAMES` to avoid duplicate resumes;
- added narrow GetObject/PutObject policy only for `operations/s11-content/{daily,historical}/*`. No deletion rights added. Deployment exposed the missing permissions and real subsequent checkpoint writes verified the repair;
- existing research-publication timer remains the general publication path. `publish_fresh.py` registered canonical new windows and published the five repaired windows immediately with existing validators.

The S11 run API now accepts a per-invocation day budget that does not alter configured checkpoint identity. **57 regression tests passed**, including identity/cursor preservation.

## Checkpoints

- Daily: `s3://data-collection-059416028963-us-east-1-an/research-data/operations/s11-content/daily/f8e1bc75867c6a0a99edb6e3859b37e052424fabdf986f7181cc7ee1b4eef231/state.json`
- Historical: `s3://data-collection-059416028963-us-east-1-an/research-data/operations/s11-content/historical/dc1198307310031731666c48d5b2535e7eff14497f9bf47ea8df3d93c220390d/state.json`

The first repaired daily receipt reports one unsupported embedded file and five unresolved company identities. These remain explicit extraction/identity gaps; candidate classifications are not confirmed corporate events. Raw source review does not certify resolved identities, complete history, or point-in-time eligibility.

## Evidence and next checks

`deployment-result.json`, worker journal results, `worker-policy-proposed.json` / `worker-policy-applied.json`, `daily-state.json`, `historical-state.json`, `tests.log`, `fresh-publication.json`, `publication.log` and `athena-after.json`.

Continue checking cursor movement, committed day receipts, publication receipts and Athena ingestion—not timer activation alone. No API-key/account action is needed from the owner. Historical completion requires ongoing scheduled processing; no guaranteed finish date is established by this sample.
