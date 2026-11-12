# November 5 — repeated HIGH notification alert

## Diagnosis

At 10:35 CET, the only high incident in the saved watchdog state was `aws:optima-collection-watchdog-delivery`. Its underlying metric is `Optima/CollectionMonitoring / NotificationErrors`.

The current error was `InvalidParameter ... Invalid parameter: Subject` during SNS email publication. The overview subject was 169 characters after the November 4 reporting change appended historical-scope counts and the historical evidence date. The digest publish path did not enforce the SNS subject limit. The last successful SNS acceptance recorded for the digest was November 3, 19:05 UTC. SMS reminders about the email-delivery alarm continued successfully.

This is a notification defect, not evidence that the 87 raw-artifact jobs all failed again. Those raw-source requirements remain separate work. The local health exporter continued inspecting all 29 configured jobs without inspection errors.

## Repair

`collection_alerts.py` now strips control characters and caps the digest's outgoing subject at 99 characters. The complete title and report remain in the durable receipt and email body. No alert was suppressed or manually closed.

31 tests passed (`test_collection_alerts`, `test_monitoring_overview`), including a regression test for oversized subjects and preserved report contents. The existing Lambda package was backed up and only `collection_alerts.py` replaced. Deployment succeeded with verified package hash. No test email or SMS was sent.

## Owner action

No key, licence, purchase or instance change is needed. Wait for the normal scheduled digest retry. Successful SNS publication is not proof of mailbox delivery; confirm the email arrives. The delivery alarm uses a 30-minute evaluation period and should clear after a successful scheduled check, provided no other notification errors occur. Live recovery is not yet verified.

If HIGH notifications continue after the next scheduled run and alarm evaluation, provide the exact alert text and received time so we can distinguish another delivery failure from this incident.

Evidence: [diagnosis](diagnosis.json), [deployment](monitoring-deployment.json), rollback package `watchdog-before.zip`.
