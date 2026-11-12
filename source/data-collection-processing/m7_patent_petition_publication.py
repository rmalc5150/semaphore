#!/usr/bin/env python3
"""Run one bounded patent-petition publication on the m7 worker."""
import json
import tempfile

from collection_storage import StorageSettings
from research_contract import ROOT, load_json
from research_publication import discover, prepare_for
from window_publication import publish_pending
import patent_prosecution_athena


OWNER = 'patent_petition_decisions'


def main():
    settings = StorageSettings.load(ROOT / 'config/collection-storage.s3.json')
    store = settings.store()
    # Discovery is intentionally limited to the prosecution manifest prefix;
    # it cannot inventory or enqueue another publisher's work.
    discovered = discover(store, settings, owners=[OWNER])
    config = load_json(ROOT / 'config/patent-petition-decisions-athena.json')
    with tempfile.TemporaryDirectory(prefix='m7-petition-publication-') as root:
        result = publish_pending(store, settings, OWNER, config,
            prepare_for(patent_prosecution_athena), root, max_windows=1)
    print(json.dumps({'m7_publication_pilot': OWNER, 'discovered': discovered,
                      'publication': result}), flush=True)
    return int(result['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
