# Shared EODHD quota and throughput

Audit and rollout: September 24, 2026. The live account reports 100,000 daily call
units. The user upgraded market-data access and requested higher utilization.

All direct network access is centralized in `EODHDClient`, used by:

| Script | Calls |
|---|---|
| `eodhd_universe.py` | Account, exchange inventory, explicit/inventory profiles |
| `eodhd_batch.py` | Planned profile cohorts with up to four workers |
| `eodhd_daily_cohort.py` | Scheduled profiles, resumptions and top-up cohorts |
| `market_collection.py` | Explicit price/dividend/split windows |
| `market_operations.py` | Scheduled current market windows and 2021 backfill |

Other EODHD-named review/coverage/Athena scripts read stored evidence; they do not
call the provider. Every production configured client now attaches `SharedQuota`.

| Allowance | Previous | Active |
|---|---:|---:|
| Profile cohort target | 7,900 symbols | Up to 8,800 symbols |
| Profile daily weighted cap | Roughly 79,000 nominal | 88,000 including retries |
| Market daily calls | 3,000 | 9,000 including retries |
| Inventory allowance | Shared residual | 1,000 |
| Combined weighted ceiling | Separate caller checks | 98,000 |
| Safety headroom below 100,000 | At least 5,000 in caller checks | 2,000 globally |
| Shared rolling minute cap | Per-client sleeps | 900 HTTP requests |

Nominal profile+market capacity rises from 82,000 to 97,000 units/day (about 18%).
This is an upper bound, not a guarantee that all capacity will be used: retries,
source errors, completed queues, S3 throughput and verification can reduce usage.

`config/eodhd-quota.json` is the runtime policy. `eodhd_quota.py` uses SQLite
transactions at `.eodhd-quota.sqlite3` to coordinate processes and threads on this
EC2 host. Reservations commit before HTTP calls. Timeouts, retries and abandoned
requests are not refunded. The ledger survives process and EC2 restarts on this
volume; do not delete it to reset quota. Multi-host collection would require a
shared external coordinator, not a separate copy of this ledger.

Provider usage refreshes can raise the local used counter, never lower reserved
usage. On initial rollout, existing provider usage is conservatively attributed
to profiles. This can reduce today's top-up but cannot reclaim earlier spending.
UTC midnight starts a separate daily ledger. EODHD may still show yesterday's
usage until the first paid request; dated prior-day readings are handled as such.
The free account endpoint counts toward the request-rate guard but not daily units.
Unknown endpoints are refused until their weighted cost is explicitly configured.

The profile timer now checks hourly, resumes the oldest unfinished pinned plan
first, then creates a separate top-up plan when today's cohort is complete and
capacity remains. Current plans, collected records and checkpoint identities are
preserved. Four profile workers are retained. Market collection runs every 15
minutes; it prioritizes current data and defers source gaps per symbol. Its quota
increase does not reset the existing market stream or re-download completed work.

Actual source costs verified in
[EODHD's API limits documentation](https://eodhd.com/financial-apis/api-limits):
fundamentals cost ten daily units even with the General filter; EOD, splits,
dividends, and exchange lists cost one; account usage costs zero. The 1,000/minute
provider limit counts HTTP requests rather than weighted daily units. The local
900/minute guard leaves headroom. No subscription or paid overage was purchased.
