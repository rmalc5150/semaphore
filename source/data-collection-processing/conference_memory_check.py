#!/usr/bin/env python3
"""Read-only S3 input, local-only conference curation memory benchmark."""
import argparse
import json
import resource
import time
from collection_storage import StorageSettings
from conference_athena import prepare
from research_contract import ROOT, load_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    args = parser.parse_args()
    settings = StorageSettings.load(ROOT / 'config/collection-storage.s3.json')
    start = time.monotonic()
    root = prepare(settings.store(), settings, load_json(ROOT / 'config/conference-athena.json'),
                   [args.manifest], ROOT / 'conference-memory-check-build')
    release = load_json(root / 'release.json')
    result = {'status': 'locally_verified', 'manifest': args.manifest,
              'records': release['files']['conference_observations']['rows'],
              'peak_rss_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
              'elapsed_seconds': round(time.monotonic() - start, 2), 'release_dir': str(root),
              'published': False}
    (ROOT / 'reports/conference-memory-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
