"""Read-only November 27 S3 rollout follow-up. Print a JSON report."""
import argparse
from collections import Counter
from decimal import Decimal
import json
import subprocess

WINDOWS = {'before': ('2026-11-14', '2026-11-20'), 'after': ('2026-11-21', '2026-11-27')}


def gather_billing():
    filters = {'And': [
        {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon Simple Storage Service']}},
        {'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': ['059416028963']}},
        {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}},
    ]}
    response = subprocess.run([
        'aws', 'ce', 'get-cost-and-usage', '--region', 'us-east-1',
        '--time-period', 'Start=2026-11-14,End=2026-11-27', '--granularity', 'DAILY',
        '--metrics', 'UsageQuantity', 'UnblendedCost',
        '--group-by', 'Type=DIMENSION,Key=USAGE_TYPE',
        '--filter', json.dumps(filters), '--output', 'json', '--no-cli-pager',
        '--cli-connect-timeout', '10', '--cli-read-timeout', '20',
    ], text=True, capture_output=True, timeout=120)
    if response.returncode:
        raise RuntimeError(response.stderr.strip()[-700:])
    return summarize_billing(json.loads(response.stdout))


def summarize_billing(response):
    output = {}
    for name, (start, end) in WINDOWS.items():
        days = [day for day in response['ResultsByTime'] if start <= day['TimePeriod']['Start'] < end]
        by_tier = {tier: {'requests': Decimal(0), 'unblended_usd': Decimal(0)} for tier in ('Tier1', 'Tier2')}
        for day in days:
            for group in day.get('Groups', []):
                for tier, totals in by_tier.items():
                    if group['Keys'][0].endswith('Requests-'+tier):
                        totals['requests'] += Decimal(group['Metrics']['UsageQuantity']['Amount'])
                        totals['unblended_usd'] += Decimal(group['Metrics']['UnblendedCost']['Amount'])
        output[name] = {'start_utc':start, 'end_utc_exclusive':end, 'days_returned':len(days),
                        'estimated_days':[day['TimePeriod']['Start'] for day in days if day.get('Estimated')],
                        'tiers':by_tier}
    if all(window['days_returned'] == 6 for window in output.values()):
        output['request_change_percent'] = {}
        for tier in ('Tier1', 'Tier2'):
            before = output['before']['tiers'][tier]['requests']
            after = output['after']['tiers'][tier]['requests']
            output['request_change_percent'][tier] = round((after-before)*100/before, 2) if before else None
    return output


def operational(start, end):
    result = subprocess.run([
        'journalctl', '--since', start+' 00:00:00 UTC', '--until', end+' 00:00:00 UTC',
        '-u', 'constellation-public-daily.service', '-u', 'optima-collection-health.service',
        '--no-pager', '-o', 'cat',
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[-700:])
    counts = Counter()
    observations = Counter()
    remaining = {}
    for line in result.stdout.splitlines():
        if not line.startswith('{'):
            continue
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if value.get('stage') == 'public_daily_s3_canary':
            observations['capture_metric_passes'] += 1
            counts.update(value['s3_requests'])
            observations['checkpoint_writes'] += value.get('checkpoint_puts', 0)
        if value.get('stage') == 'public_daily_idle_backoff':
            observations['idle_skips'] += 1
        if 'daily_public_sources' in value:
            observations['capture_reports'] += 1
            for row in value['daily_public_sources']:
                if 'remaining_urls' in row:
                    remaining[row['source']] = row['remaining_urls']
                observations['attempts_reported'] += row.get('attempts', 0)
                observations['source_errors'] += int('error' in row)
        if 's3_batch_checks' in value:
            observations['health_metric_passes'] += 1
            observations.update({'health_'+k:v for k,v in value['s3_batch_checks'].items()})
            observations['health_inspection_errors'] += len(value.get('inspection_errors', {}))
    return {'public_capture_sdk_operations': dict(counts), 'observations': dict(observations),
            'latest_public_frontier_by_observed_source': remaining,
            'journal_note': result.stderr.strip() or None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs-only', action='store_true', help='Smoke-test journal collection without AWS billing calls.')
    args = parser.parse_args()
    report = {'operational':{}, 'billing':None}
    for name, dates in WINDOWS.items():
        try:
            report['operational'][name] = operational(*dates)
        except (RuntimeError, subprocess.SubprocessError) as error:
            report['operational'][name] = {'error':str(error)}
    if not args.logs_only:
        try:
            report['billing'] = gather_billing()
        except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as error:
            report['billing'] = {'error':str(error), 'action':'Verify AWS billing credentials and rerun the report.'}
    print(json.dumps(report, indent=2, default=str))


if __name__ == '__main__':
    main()
