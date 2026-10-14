#!/usr/bin/env python3
"""Observe collection cgroups without starting, stopping or limiting any jobs."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent


def sample(units):
    mem = {k: int(v.split()[0]) * 1024 for k, v in
           (line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())}
    jobs = {}
    for unit in units:
        candidates = [Path('/sys/fs/cgroup/optima.slice/optima-data.slice') / unit,
                      Path('/sys/fs/cgroup/system.slice') / unit]
        cg = next((p for p in candidates if (p / 'memory.current').exists()), candidates[0])
        try:
            current = int((cg / 'memory.current').read_text())
            peak = int((cg / 'memory.peak').read_text())
            stat = dict(line.split() for line in (cg / 'memory.stat').read_text().splitlines())
        except FileNotFoundError:
            continue
        jobs[unit] = {'current_bytes': current, 'cgroup_peak_bytes': peak,
                      'anon_bytes': int(stat['anon']), 'file_bytes': int(stat['file'])}
    return {'at': datetime.now(timezone.utc).isoformat(), 'jobs': jobs,
            'host_nonfree_bytes': mem['MemTotal'] - mem['MemFree'],
            'host_unavailable_bytes': mem['MemTotal'] - mem['MemAvailable'],
            'host_available_bytes': mem['MemAvailable'],
            'concurrent_jobs_bytes': sum(j['current_bytes'] for j in jobs.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=int, default=900)
    parser.add_argument('--interval', type=int, default=5)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/ram-observation-2026-09-24.json')
    args = parser.parse_args()
    if not 1 <= args.duration <= 86400 or not 1 <= args.interval <= 60:
        parser.error('duration must be 1..86400 seconds; interval 1..60')
    units = sorted(p.name for p in (ROOT / 'systemd').glob('optima-*.service'))
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'target_bytes': 4000000000,
              'mode': 'read_only_observation', 'samples': 0, 'complete': False,
              'units': {u: {'observed_active_samples': 0, 'peak_cgroup_bytes': None} for u in units},
              'max_host_nonfree_bytes': 0, 'max_host_unavailable_bytes': 0, 'max_concurrent_jobs_bytes': 0}
    destination = args.output
    deadline = time.monotonic() + args.duration
    while True:
        current = sample(units); report['samples'] += 1; report['latest'] = current
        for field in ('host_nonfree_bytes', 'host_unavailable_bytes', 'concurrent_jobs_bytes'):
            report['max_' + field] = max(report['max_' + field], current[field])
        for unit, data in current['jobs'].items():
            item = report['units'][unit]; item['observed_active_samples'] += 1
            item['peak_cgroup_bytes'] = max(item['peak_cgroup_bytes'] or 0, data['cgroup_peak_bytes'])
            item['last_observed_at'] = current['at']
        report['complete'] = time.monotonic() >= deadline
        temporary = destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, indent=2) + '\n'); os.replace(temporary, destination)
        if report['complete']:
            break
        time.sleep(min(args.interval, max(0, deadline - time.monotonic())))
    print(json.dumps({'report': str(destination), 'samples': report['samples']}))


if __name__ == '__main__':
    main()
