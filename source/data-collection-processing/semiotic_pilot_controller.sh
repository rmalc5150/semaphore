#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
socket=${1:?Pass the private worker SSH control socket}
workdir=${2:?Pass the controller handoff directory}
profiles=${3:-config/semiotic-pilot-v1.json}
worker=ec2-user@172.31.44.203
if [[ ! -f "$workdir/handoff.json" ]]; then
    .venv-athena/bin/python -u semiotic_pilot.py prepare --config config/metadata-engine.json \
        --profiles "$profiles" --output "$workdir"
fi
read -r digest _ < <(sha256sum "$workdir/handoff.json")
remote="pilot-v1/jobs/$digest"
ssh -S "$socket" -o BatchMode=yes "$worker" "mkdir -p ~/semiotic-run/$remote"
tar -C "$workdir" -cf - handoff.json archive | ssh -S "$socket" -o BatchMode=yes "$worker" \
    "tar -C ~/semiotic-run/$remote -xf - && cd ~/semiotic-run/$remote && echo '$digest  handoff.json' | sha256sum -c -"
ssh -S "$socket" -o BatchMode=yes "$worker" \
    "cd ~/semiotic-run && mkdir -p $remote/output && flock -n $remote/run.lock bash pilot-v1/app/semiotic_pilot_worker.sh $remote > $remote/output/run.log 2>&1"
printf '%s\n' "$remote"
