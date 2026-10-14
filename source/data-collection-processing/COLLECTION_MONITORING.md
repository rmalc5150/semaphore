# Collection monitoring

Deployment status (2026-09-26): **The independent watchdog and email alerts are
operational. SMS subscriptions exist for both numbers, but AWS reports delivery
failures for both US and Spain; SMS is not operational yet.** Email receipt has
been confirmed by the recipient. Both phone numbers received no test texts.

The account is outside the SMS sandbox. Actual `AWS/SNS` `SMSSuccessRate` metrics
with `Country=US/ES` and `SMSType=Transactional` are zero for the test sends.
Two email-only CloudWatch alarms now monitor these SMS failures. SNS publish API
acceptance and the topic's delivery metric alone do not establish handset delivery.

The consolidated permissions are installed and SMS delivery logging is enabled.
On 2026-09-26 at 10:28 UTC, AWS accepted toll-free registration
`registration-3ebe8dc67b2b4cc29bbaf6d5847a3257` for **+1 833-962-1446**.
The number costs $2/month plus usage, is associated with the registration, and has
an SNS resource policy restricted to this AWS account. Registration is SUBMITTED;
the number is PENDING. No further permission correction is currently required.
Carrier approval and successful delivery tests remain necessary before SMS is operational.
Reviewed terms and the SMS privacy notice are publicly available in the dedicated
legal-pages bucket. All 25 registration fields and the workflow attachment are saved.

The earlier US test failed because no origination identity was available. The
Spanish test separately reported Movistar: `Phone carrier is currently
unreachable/unavailable`. Spanish delivery remains unresolved; the US number has
international sending disabled and does not establish a fix for Spain.
Email and all monitoring schedules remain operational during carrier review.

## Installed now

- `optima-collection-health.timer`: every 30 minutes, at :00 and :30 UTC.
- Inspects all 15 collection/publication timers, services, recent source outcomes,
  current stream checkpoints, publication queues, and sampled committed evidence.
- S3 destination: `s3://data-collection-059416028963-us-east-1-an/research-data/monitoring/`.
- `health/latest.json`: latest server report; does not claim complete data coverage.
- `state/latest.json`: most recent check, active incidents, notification state,
  and progress comparison. This replaces DynamoDB.
- `alerts/YYYY-MM-DD/*.json`: alert/delivery history. `checks/YYYY-MM-DD/*.json`:
  check history. Both expire after 30 days.
- Every check explicitly deletes history files older than 30 days; S3 lifecycle
  expiration is a backup. The bucket is unversioned. The deletion worker only has
  access to these two monitoring history prefixes. Collection data is outside its
  deletion scope. If versioning is enabled later, version cleanup must be added.
- The current state and current heartbeat are operational pointers, kept outside
  the expiring history. An unresolved incident remains in current state until
  recovery; its historical alert files still expire normally.
- The temporary `local-recorder.conf` drop-in has been removed from the installed
  service. Only the independent Lambda writes current alert state and sends alerts.

## Deployment and updates

Use this single consolidated policy for `lambdaEc2ForEc2Instance`; it supersedes
the three earlier deployment, SMS, and SMS-diagnostics policy files:
[`config/collection-monitoring-permissions.json`](config/collection-monitoring-permissions.json)
It covers deployment, SMS dependencies and delivery diagnostics, three dedicated
service roles, the monitoring topics/function/schedule/alarms, log inspection,
S3 health evidence reads, monitoring writes, and retention. Object deletion stays
restricted to the alert/check history prefixes. SMS backend actions remain
restricted to requests through SNS. The consolidated policy is 6,035 characters
excluding whitespace and fits the customer-managed policy size limit.

The policy generator (`deploy_collection_monitoring.py --permissions`) now writes
only this consolidated file. Replace the previous monitoring deployment inline
policy with this document; the separate monitoring supplements are then redundant.
Existing collector/application policies are outside this consolidation.

Administrator CLI (run from this project with an authorized administrator identity):

```sh
aws iam put-role-policy \
  --role-name lambdaEc2ForEc2Instance \
  --policy-name OptimaCollectionMonitoringDeployment \
  --policy-document file://config/collection-monitoring-permissions.json
```

Then, using the instance's usual identity:

```sh
.venv-athena/bin/python deploy_collection_monitoring.py
```

The deployment creates:

- SNS standard topics `optima-collection-alerts-email` and
  `optima-collection-alerts-sms`. Routine incidents go to
  `randall@optima-holdings.com`; high-severity incidents also go to `+13104033167` and `+34617895324`.
  Both phone subscriptions are active, but actual delivery currently fails.
- Lambda `optima-collection-watchdog`, with reserved concurrency 1 to serialize
  S3 state updates. It has no permission to modify collector data.
- EventBridge Scheduler `optima-collection-watchdog-30min` at :05/:35 UTC, giving
  the server's :00/:30 report time to complete. Both checks repeat every 30 minutes.
- CloudWatch alarms for Lambda errors, missing watchdog completions, and SNS
  publish errors. These go directly to both topics independently of watchdog code.
- A 30-day Lambda log retention policy.

The deployment removes the temporary local state writer before activating the
independent watchdog. It invokes the Lambda once and records verification in
`reports/collection-monitoring-deployment.json`. Deployment is safe to rerun.

The email recipient has confirmed the SNS subscription and received messages.
The account is outside the SMS sandbox. US origination identity/registration and
carrier delivery still need to be checked if the recipient does not receive texts. SNS accepting a message
is not proof of handset/inbox delivery. Confirm receipt of a labeled test before
considering both notification routes fully operational.

## Alert behavior

- Disabled timers, missed invocations, queue timeouts, failed processes, nested
  source failures, unresolved market coverage, and stalled publication are low
  severity. OOM kills, integrity/verification mismatches, and a missing host
  heartbeat are high severity.
- The host heartbeat must be at most 45 minutes old. The 30-minute cloud poll
  detects an outage on its first poll after that grace period.
- A queue wait is distinct from payload runtime. Existing execution deadlines and
  six-hour queue allowances remain in effect. The monitor adds 30 minutes of
  grace before declaring a currently running/waiting invocation overdue.
- Idle jobs must start within 12 hours, or 36 hours for daily jobs. Pending work
  without changed committed progress gets the same thresholds. These conservative
  initial thresholds accommodate the existing shared heavy-job lock.
- Normal daily quota deferrals receive at least 36 hours before a progress-stall
  alert, allowing the next UTC reset plus queue time. Lock-busy and bounded batch
  stops do not themselves constitute failures.
- One incident per service/error is remembered in S3, with immediate critical SMS (six-hour SMS reminders) and consolidated
  12-hour email digests including recoveries. A restart alone does not resolve a data failure; the check must
  observe newer committed manifest or verified publication evidence.
- If reading a job fails or the host disappears, existing incidents remain open.
- Notification failures remain pending and retry on the next check. Delivery is
  at-least-once: a crash after SNS acceptance but before saving state can duplicate
  an alert. Different failures in the same pipeline can produce separate alerts.
- This is operational monitoring with sampled evidence checks, not an exhaustive
  audit of every record or source's coverage. It never fetches paid source data.

## Operations and verification

```sh
systemctl list-timers optima-collection-health.timer --no-pager
journalctl -u optima-collection-health.service -n 20 --no-pager
.venv-athena/bin/python -m unittest test_collection_alerts -v
```

`reports/collection-monitoring-live-verification.json` records the deployed AWS resources and live S3 check;
`reports/collection-monitoring-delivery-tests.json` records SNS acceptance of the test messages;
`reports/collection-monitoring-tests.log` records the automated tests. The first
installed service run completed successfully with all 15 jobs inspected and no
inspection errors. It recorded the remaining market coverage and NMPA incidents.

When collector configuration, stream identities, or scheduling changes, rerun
`build_collection_monitoring_config.py`, review its generated configuration, and
redeploy the Lambda. The health exporter reads configuration afresh each time.
To pause only monitoring, stop/disable `optima-collection-health.timer` and disable
the corresponding EventBridge schedule and watchdog alarms together. Collection
timers are independent.

AWS references:
[SNS email confirmation](https://docs.aws.amazon.com/sns/latest/dg/sns-email-notifications.html),
[SMS sandbox](https://docs.aws.amazon.com/sns/latest/dg/sns-sms-sandbox.html),
[S3 asynchronous lifecycle expiration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html),
[Scheduler Lambda invocation](https://docs.aws.amazon.com/lambda/latest/dg/with-eventbridge-scheduler.html).

SNS underlying SMS permission reference: [AWS SNS managed policy dependencies](https://docs.aws.amazon.com/sns/latest/dg/security-iam-awsmanpol.html).

The consolidated policy now also covers US sender registration and provisioning.
New resources must be tagged `Project=OptimaCollectionMonitoring`; edits and
submission are restricted to matching registration/attachment/phone resources.
These permissions extend the existing SNS delivery/diagnostic permissions.

### SMS registration progress — 2026-09-26

Registration submission succeeded after the consolidated IAM correction was installed.
See `reports/collection-monitoring-sms-registration-live.json` for AWS responses,
resource IDs, public legal-page URLs, number association, and submission timestamp.
The enrollment illustration is explicitly not a signed consent record. The estimated
monthly volume is 100. The dedicated public S3 policy permits reads only of the two
legal pages; collection bucket access was unchanged. Published pages exclude the EIN
and recipient numbers.

To refresh registration and number status without creating duplicate resources:

```sh
.venv-athena/bin/python register_collection_sms.py
```

The script persists resource IDs and idempotency tokens. Approval and recipient
delivery tests are still required. Spain's carrier failure remains separate.

### US-only destination change — 2026-09-26

At the account owner's request, local and deployed Lambda configuration now retain
only +13104033167 and country US. Spain delivery alarm actions are disabled.
The Spanish SNS subscription was removed after the updated policy was installed.
SNS now has exactly one SMS recipient: +13104033167. The consolidated policy
includes `sns:Unsubscribe` on the monitoring topics. Local and deployed configuration
both retain only the US recipient. See `reports/collection-monitoring-us-only.json`.
Spain troubleshooting is no longer in scope. US sender carrier approval remains pending.

### Scheduled SMS follow-up

`optima-sms-followup.timer` runs once on 2026-10-19 at 10:30 UTC: 15 weekdays
after September 26, excluding the October 12 US federal holiday. It reads AWS
registration/number status, current SMS recipients, and seven days of US delivery
metrics; saves the report under the 30-day S3 checks prefix; and emails the
confirmed monitoring email topic. Preview passed without sending a message.
The persistent timer catches up after host downtime; failed executions retry twice
at five-minute intervals. It does not claim handset delivery based on approval alone.

### Textless PDF pages — user policy, 2026-09-26

Skip pages without extractable text and record skipped page numbers in document
metadata. Do not emit `document_requires_ocr_or_page_review`. The deployed watchdog
silently retires existing incidents with that code; it does not claim the old
collection run recovered. Other source errors remain monitored. Raw document
evidence is retained, and scanned pages are not OCR-processed under this policy.

### Consolidated email reporting — 2026-09-26

Checks continue every 30 minutes. `email_digest_seconds=43200` batches all email
incidents into one message per 12-hour window, starting at deployment. Current
incidents are deduplicated by service/error code; incidents that recover during
the window remain in the summary. Empty windows send no email. Active unresolved
incidents appear in the next summary. S3 state stores the accumulated digest and
failed sends retry on the next check without discarding entries. Full digest
history remains under alerts/ with 30-day retention.

Critical SMS remains immediate with the existing six-hour reminder interval.
CloudWatch infrastructure alarms retain direct critical SMS but no direct email;
US carrier-delivery alarms are included in the digest. The watchdog has scoped
DescribeAlarms access for these monitoring alarms. Missing-watchdog alerts still
have their independent SMS path. The scheduled October 19 SMS follow-up remains
a separate one-time email explicitly requested by the user.
