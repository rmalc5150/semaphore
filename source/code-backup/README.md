# EC2 source backup

Run `python3 /home/ec2-user/code-backup/backup.py` to commit and push the current source snapshot to `git@github.com:rmalc5150/semaphore.git`, branch `ec2-code-backup`. Existing branches are preserved; pushes never force changes. Each changed snapshot is a separate commit. An unchanged run still retries any pending push.

First add `/home/ec2-user/.ssh/semaphore_backup.pub` as a deploy key with **Allow write access** in the repository's Settings → Deploy keys. The private key stays on this instance. GitHub host keys are installed in `~/.ssh/known_hosts` from GitHub's HTTPS API.

Preview and check selection without a network connection:

```sh
python3 /home/ec2-user/code-backup/backup.py --dry-run
```

Selection recursively covers nonhidden folders under `/home/ec2-user`, including archived source and this script. Source extensions, documentation, JSON configuration, SQL, requirements, and systemd definitions are included. Hidden folders, symlinks, virtual environments, dependencies, build folders, reports, databases, certificates, environment files, and files named for credentials or secrets are excluded. Files over 10 MiB and likely embedded credentials stop the run for review. The credential check is heuristic; inspect the dry-run selection when adding new projects. Extend `EXTENSIONS`, `NAMES`, and `SKIP` in the script as needed.

The Git working copy and process lock live in `~/.local/state/code-backup/`. A SHA-256 manifest accompanies each snapshot. Concurrent runs are rejected. Credentials, collected data, and live machine configuration are not backed up, so recovery needs those provisioned separately. Code outside `/home/ec2-user` is not included.

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
