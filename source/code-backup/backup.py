#!/usr/bin/env python3
"""Snapshot local source files and push them to the EC2 backup branch."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from datetime import datetime, timezone

ROOT = Path('/home/ec2-user')
STATE = ROOT / '.local/state/code-backup'
REPO = STATE / 'repository'
REMOTE = 'git@github.com:rmalc5150/semaphore.git'
BRANCH = 'ec2-code-backup'
EXTENSIONS = {'.py', '.sh', '.bash', '.sql', '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.service', '.timer', '.socket', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.scss', '.rs', '.go', '.java', '.c', '.h', '.cpp', '.ipynb', '.r', '.tf', '.hcl'}
NAMES = {'Dockerfile', 'Makefile', 'Procfile', 'LICENSE', 'Pipfile', 'poetry.lock', 'uv.lock', 'package-lock.json', '.gitignore', '.dockerignore'}
SKIP = {'node_modules', '__pycache__', 'venv', 'env', 'dist', 'build', 'target', 'reports', 'certs', 'site-packages'}
SECRET = re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}|\bsk-[A-Za-z0-9_-]{24,}|(?i:(?:password|passwd|api[_-]?key|secret[_-]?key|access[_-]?token)\s*[=:]\s*[\"\x27])[^\"\x27\n]{12,}[\"\x27]')

def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)

def collect():
    files = []
    for directory, dirs, names in os.walk(ROOT, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in SKIP and not d.endswith('-build') and not (Path(directory) / d).is_symlink())
        for name in sorted(names):
            path = Path(directory) / name
            if path.is_symlink() or (name.startswith('.') and name not in NAMES):
                continue
            if name not in NAMES and path.suffix.lower() not in EXTENSIONS:
                continue
            if any(x in name.lower() for x in ('credentials', 'secrets', '.env', 'token.json')):
                continue
            if path.stat().st_size > 10 * 1024 * 1024:
                raise RuntimeError(f'Source file exceeds 10 MiB; review selection: {path.relative_to(ROOT)}')
            data = path.read_bytes()
            matches = SECRET.finditer(data.decode('utf-8', errors='replace'))
            if any(m.group() != 'api_key="secret-test-value"' for m in matches):
                raise RuntimeError(f'Possible embedded credential; move it to an excluded environment file first: {path.relative_to(ROOT)}')
            files.append((path.relative_to(ROOT), data, path.stat().st_mode & 0o111))
    return files

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='check and list selected files without Git or network access')
    args = parser.parse_args()
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / 'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        files = collect()
        if args.dry_run:
            for path, _, _ in files:
                print(path)
            print(f'{len(files)} files; {sum(len(data) for _, data, _ in files):,} bytes')
            return
        os.environ.setdefault('GIT_SSH_COMMAND', f'ssh -F /dev/null -i {ROOT}/.ssh/semaphore_backup -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15')
        if not (REPO / '.git').exists():
            REPO.mkdir(parents=True, exist_ok=True)
            run('git', 'init', '-b', BRANCH, str(REPO))
            run('git', '-C', str(REPO), 'remote', 'add', 'origin', REMOTE)
        def git(*commands, **kwargs):
            return run('git', '-C', str(REPO), *commands, **kwargs)
        git('config', 'user.name', 'EC2 Code Backup')
        git('config', 'user.email', 'ec2-backup@localhost')
        # Check remote access before modifying the local snapshot.
        refs = git('ls-remote', '--heads', 'origin', f'refs/heads/{BRANCH}', stdout=subprocess.PIPE, text=True).stdout
        if refs:
            git('fetch', 'origin', BRANCH)
            git('merge', '--ff-only', 'FETCH_HEAD')
        snapshot = REPO / 'source'
        if snapshot.exists():
            shutil.rmtree(snapshot)
        manifest = []
        for path, data, executable in files:
            destination = snapshot / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            destination.chmod(0o755 if executable else 0o644)
            manifest.append({'path': str(path), 'sha256': hashlib.sha256(data).hexdigest()})
        (REPO / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        git('add', '--all')
        changed = subprocess.run(['git', '-C', str(REPO), 'diff', '--cached', '--quiet']).returncode
        if changed == 1:
            git('commit', '-m', 'EC2 source snapshot ' + datetime.now(timezone.utc).isoformat())
        elif changed != 0:
            raise RuntimeError('Cannot inspect staged changes')
        git('push', 'origin', f'HEAD:refs/heads/{BRANCH}')
        print(f'Backup verified and pushed: {len(files)} files on {BRANCH}')

if __name__ == '__main__':
    main()
