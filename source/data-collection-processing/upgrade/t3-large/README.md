# Prepared upgrade: t3.medium → t3.large

Target: **i-070bab0b09f794629**, **us-east-1**, availability zone **us-east-1d**.

Prepared October 21, 2026. Collection is still running. No stop, resize, maintenance guard or memory-limit change has been applied. Read-only preflight found 70 active timers and 73 timer-associated services.

## Prepared configuration

- Instance: t3.large, 2 vCPUs, 8 GiB RAM.
- Shared `optima-data.slice`: MemoryHigh=5 GiB; MemoryMax=6 GiB; swap disabled.
- S3-supervised heavy Optima workers: MemoryHigh=4 GiB; MemoryMax=5 GiB.
- Independent health-monitor and code-backup memory limits stay unchanged.
- Existing global serialization remains intact. This upgrade addresses memory capacity; it does not automatically eliminate queue or provider failures.
- Overrides are separate `zz-t3-large-memory.conf` files, so existing runtime guards remain intact. The application step refuses to change limits unless the machine identifies as t3.large and exposes at least 7 GiB of RAM.
- `/dev/shm` normally grows to approximately half of physical memory after boot. It remains part of the same RAM budget, not extra memory. Check its actual capacity after resizing.

## Step 1 — Prepare the maintenance window

Run as ec2-user (the script uses sudo for systemd; do not run the whole Python interpreter as root):

```bash
cd /home/ec2-user/data-collection-processing
.venv-athena/bin/python upgrade/t3-large/prepare.py inspect
.venv-athena/bin/python upgrade/t3-large/prepare.py quiesce
```

This snapshots timer state on persistent disk, installs persistent maintenance conditions, stops timers, gracefully stops workers using their configured SIGINT handling, recovers retained RAM via the existing S3 runtime, and verifies the current S3 pointer against its immutable checkpoint manifest. It does not send notifications or change the EC2 instance.

**Proceed only when it prints `ready_to_stop` and creates `ready-to-stop.json`.** If it fails, leave the instance running. Do not force-stop, reboot, delete `/dev/shm`, or discard `pending.json`; investigate the checkpoint error first. The readiness result is valid only while maintenance remains active and no work has been manually started outside the supervised services.

Timers stay enabled but their workers are guarded across reboot. This avoids changing which schedules were originally enabled. Collection can remain paused while you complete the console steps.

To abandon the resize before stopping the instance, run `prepare.py resume`; this restores previously active timers with the old memory limits.

## Step 2 — Resize in AWS

1. Open EC2 in **us-east-1** and select **i-070bab0b09f794629**.
2. Confirm Step 1 succeeded. Choose **Instance state → Stop instance** (not terminate), and wait for **Stopped**.
3. Choose **Actions → Instance settings → Change instance type**, select **t3.large**, and apply.
4. Start the instance and wait for its status checks to pass.
5. Reconnect with your normal EC2/IDE method. If an automatically assigned public IP changed, use the new address shown in EC2. An Elastic IP, if attached, remains the connection address.

Do not change architecture, AMI, storage or IAM role as part of this resize.

## Step 3 — Apply guarded memory limits, then resume

```bash
cd /home/ec2-user/data-collection-processing
.venv-athena/bin/python upgrade/t3-large/prepare.py inspect
.venv-athena/bin/python upgrade/t3-large/prepare.py apply
.venv-athena/bin/python upgrade/t3-large/prepare.py resume
```

`apply` verifies the actual systemd limits and saves `limits-applied.json`. It leaves maintenance active if any check fails. `resume` removes the maintenance marker and restarts only the timers that were active before maintenance; it also schedules a fresh health inspection.

## Step 4 — Verify recovery

```bash
free -h
df -h /dev/shm
sudo systemctl show optima-data.slice -p MemoryHigh -p MemoryMax
sudo systemctl show optima-authenticated-daily.service -p MemoryHigh -p MemoryMax
sudo systemctl list-timers 'optima*' --all --no-pager
sudo journalctl -u optima-collection-health.service -n 10 --no-pager
```

Expected shared MemoryMax: **6442450944**; heavy-worker MemoryMax: **5368709120**. Expect approximately 8 GiB installed RAM (slightly less visible to Linux). Confirm subsequent collector runs commit to S3 and their publishers produce successful Athena receipts. Keep existing SQL source checks for semantic validation. Neither an active timer nor the hardware change proves a previously failing source has recovered.

## Recovery and rollback

- Before resizing: `resume` cancels maintenance without changing memory limits.
- After resizing: if memory application fails, keep maintenance active and repair the reported failure; do not bypass the hardware check.
- Before any downgrade back to t3.medium, repeat a verified maintenance checkpoint and remove only the new `zz-t3-large-memory.conf` overrides, then reload systemd and verify the original limits. Do not leave a 6 GiB allowance on a 4 GiB host.
- Keep the saved state, checkpoint receipt and any `.before` backup files for diagnosis. A second maintenance session must archive the prior state deliberately; the script refuses silently to reuse old timer snapshots.

Tests verify the hardware guard and refusal to apply oversized limits on t3.medium. The maintenance/resize itself has not been rehearsed against production because it interrupts collection.
