#!/usr/bin/env python3
"""Independently publish completed news windows, retrying failed releases."""
import fcntl
import json
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from news_athena import prepare
from window_publication import publish_pending


def main():
    with (ROOT/'.news-athena.lock').open('a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return 2
        settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json')
        result=publish_pending(settings.store(),settings,'news',load_json(ROOT/'config/news-athena.json'),prepare,ROOT/'news-window-build',2)
        print(json.dumps(result),flush=True)
        import boto3
        from news_operations import NewsOperations
        from finlight_backfill import check_completion
        monitor = load_json(ROOT/'config/collection-monitoring.json')
        completion = check_completion(
            NewsOperations(settings.store(), settings, load_json(ROOT/'config/news-operations.json')),
            boto3.client('sns', region_name=monitor.get('region', 'us-east-1')),
            monitor.get('email_topic_arn'))
        print(json.dumps({'finlight_backfill': completion}), flush=True)
        return 1 if result['status']=='failed' else 0

if __name__=='__main__': raise SystemExit(main())
