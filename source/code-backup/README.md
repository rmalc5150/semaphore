# EC2 source backup

The scheduled backup uses the November 13 replacement SSH deploy key (`~/.ssh/semaphore_backup_20261113`). The GitHub App integration remains pending. The November 13 incident notes below record earlier access failures.

## Historical incident — GitHub App installation blocked, 13 November 2026

GitHub displays **“No accounts available. You have no accounts available for installation.”** App authentication still succeeds; API metadata confirms owner `rmalc5150` and zero installations. A separate unauthenticated request for `/users/rmalc5150` also returns HTTP 404. These observations suggest an account visibility/installation-eligibility problem, but do not prove its cause.

Confirm the browser is signed in as `rmalc5150`; a private app can be installed only on its owning account. If the correct owner is signed in and still cannot select the account, add the following to the existing GitHub Support request:

> App 5743112 (Optima EC2 Backup), owned by rmalc5150, authenticates successfully and has Contents: write. Install App displays “No accounts available. You have no accounts available for installation.” The app has zero installations. GET https://api.github.com/users/rmalc5150 also returns 404. SSH deploy-key authentication succeeds, but repository read/write return Repository not found. Please investigate account installation eligibility and any remaining security restriction following the required password reset.

The App-backed worker is prepared but not active; no App-backed push has succeeded. This supersedes the earlier assumption that the owner simply needed to click Install.

## GitHub App setup — 13 November 2026

App **5743112 / Optima EC2 Backup** authenticates successfully with its private key in AWS Secrets Manager (`githubAPP`). GitHub confirms app permissions **Contents: write / Metadata: read**. The app has **zero installations**, so its repository-installation endpoint returns HTTP 404. This is a missing setup step; it is separate from the earlier SSH-key failures.

**Owner action:** open [Install App](https://github.com/settings/apps/optima-ec2-backup/installations), choose the `rmalc5150` account, select **Only select repositories → semaphore**, and click **Install**.

The App authentication code is prepared and eight tests pass. `github-app.pending.json` contains only non-secret identifiers; production still uses the existing configuration until an App-backed push is verified. The worker retrieves the private key into memory, signs a short-lived JWT, discovers the installation, requests a token limited to the target repository with Contents: write, and uses HTTPS Git with an askpass helper. Tokens/private keys are never embedded in Git URLs or saved in Git configuration. Tokens refresh before expiry. Each push must pass an independent remote branch SHA comparison before a success receipt is written.

After installation, run the bounded backup with `--auth-config /home/ec2-user/code-backup/github-app.pending.json` under the existing supervised runtime; after successful push/readback, activate `github-app.json` and rerun the actual daily service. Do not treat unit exit zero, SSH authentication or an API metadata response as push verification.


## Replacement key requested — 13 November 2026

A new Ed25519 pair was generated at the owner's request. Add the public key from `/home/ec2-user/.ssh/semaphore_backup_20261113.pub` to this repository's **Settings → Deploy keys**, with **Allow write access** enabled. Suggested title: `EC2 backup — November 13, 2026`. Fingerprint: `SHA256:7+2QgysKC1rPfLXh6V7k9cC00EBN1kOAYKuXxNI4zqk`.

The owner registered the replacement key. Live tests confirm SSH authentication as `rmalc5150/semaphore`, but repository read and write still return `Repository not found`; SSH-over-443 produces the same result. The owner authorized switching only if it works, so the production key has **not** been changed. No push succeeded. Both old and replacement keys exhibit the same repository-access denial; further key rotation is not supported by these results. The next owner action is GitHub Support after checking account-recovery requirements. Include the replacement key fingerprint above in the existing support diagnostic.

## Current access check — 13 November 2026

**GitHub access is still not restored.** The existing SSH deploy key authenticates as `rmalc5150/semaphore`, but both repository read (`git ls-remote`) and write (`git-receive-pack` reference advertisement) return `Repository not found`. No source files or branch changes were sent. The daily timer remains enabled/active; its next run is November 14 at 03:00 Europe/Madrid (02:00 UTC). The failed scheduled execution remains visible until an actual successful backup replaces it.

A current credential-scanned local snapshot is preserved in `.pending/source-2026-11-13T104600297349Z.tar.gz`: **4,014 source files**, with every archived member checked against its SHA-256 manifest. Its adjacent `.receipt.json` records the archive checksum and explicitly says `uploaded: false`. This is a local safeguard, not an off-instance backup. November 12's snapshot is retained too.

Owner steps:

1. Sign in as the repository owner and open [rmalc5150/semaphore](https://github.com/rmalc5150/semaphore). Resolve any remaining account-recovery notice. If the repository moved, provide the current SSH clone URL.
2. The URL and deploy key were already confirmed and the key re-added on November 12. If those details are unchanged, avoid repeating key rotation. Confirm its existing **Allow write access** setting; however, a write-only permission issue would not explain the failed read probe.
3. If the repository is accessible in your browser and account recovery is complete, send GitHub Support this diagnostic:

   > SSH authenticates as rmalc5150/semaphore, but both git ls-remote and git-receive-pack for git@github.com:rmalc5150/semaphore.git return Repository not found. This persisted on November 13, 2026 after the required password reset and deploy-key re-addition. Please investigate any remaining account/repository restriction. Public key fingerprint: SHA256:G9ixQupbhkXbA6G8C4xSAhQZFcsYgZwaJWalGqdmJBk.

The precise cause is unconfirmed. [GitHub's error guidance](https://docs.github.com/en/repositories/creating-and-managing-repositories/troubleshooting-cloning-errors#error-repository-not-found) distinguishes repository existence/URL and permission problems; [deploy-key guidance](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys) explains write access. Do not send private keys to support.

Once access is repaired, run the existing backup service and verify the remote `ec2-code-backup` branch matches the pushed commit. A successful SSH greeting alone is insufficient. The owner-paused GitHub data-source collector is separate and remains paused.

## Operation and recovery

Run `python3 /home/ec2-user/code-backup/backup.py` to commit and push the current source snapshot to `git@github.com:rmalc5150/semaphore.git`, branch `ec2-code-backup`. Existing branches are preserved; pushes never force changes. Each changed snapshot is a separate commit. An unchanged run still retries any pending push.

The public key for the current deploy key is `/home/ec2-user/.ssh/semaphore_backup_20261113.pub`. On a replacement instance, provision a deploy key with **Allow write access** in the repository's Settings → Deploy keys. The private key stays on the instance. GitHub host keys are installed in `~/.ssh/known_hosts` from GitHub's HTTPS API.

Preview and check selection without a network connection:

```sh
python3 /home/ec2-user/code-backup/backup.py --dry-run
```

Selection recursively covers nonhidden folders under `/home/ec2-user`, including archived source and this script. Source extensions, documentation, JSON configuration, SQL, requirements, and systemd definitions are included. Hidden folders, symlinks, virtual environments, dependencies, build folders, reports, databases, certificates, environment files, and files named for credentials or secrets are excluded. Under `hybrid-assets`, the downloaded E5 `tokenizer.json` and the local dependency installs (`nlp/` and `packages/`) are excluded. The `stage.py` download script is included. Selected files over 10 MiB and likely embedded credentials stop the run for review. The credential check is heuristic; inspect the dry-run selection when adding new projects. Extend `EXTENSIONS`, `NAMES`, and `SKIP` in the script as needed.

The Git working copy and process lock default to `/dev/shm/optima-s3/work/tmp/code-backup/`, inside the supervised S3 runtime; `CODE_BACKUP_STATE_DIR` can override that directory. A SHA-256 manifest accompanies each snapshot. Concurrent runs are rejected. Credentials, collected data, and live machine configuration are not backed up, so recovery needs those provisioned separately. Code outside `/home/ec2-user` is not included.

The systemd timer `ec2-code-backup.timer` runs daily at **03:00 Europe/Madrid**, including daylight saving changes. It starts automatically after reboot and catches up on a missed run when the timer starts. The service runs as `ec2-user`; errors and output go to the system journal.

```sh
systemctl list-timers ec2-code-backup.timer
sudo journalctl -u ec2-code-backup.service -n 50 --no-pager
sudo systemctl start ec2-code-backup.service
```

The service and timer definitions are kept alongside this script. To reinstall them on a replacement instance after setting up Git and SSH access:

```sh
sudo install -m 0644 /home/ec2-user/code-backup/ec2-code-backup.service /home/ec2-user/code-backup/ec2-code-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ec2-code-backup.timer
```

To recover, clone the repository with `git clone --branch ec2-code-backup git@github.com:rmalc5150/semaphore.git` and restore files from `source/`. Previous versions are retained in Git history. Recreate environments from requirements files and supply credentials separately.
