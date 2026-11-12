"""Seed the approved catalog and unaudited coverage cells without replacing audits."""
import json

from constellation.catalog import ROOT, coverage
from constellation.control import Control, canonical, job_id


def main():
    registry = json.loads((ROOT / 'config/constellation-source-registry.json').read_text())
    control = Control()
    with control.db() as cursor:
        cursor.executemany('INSERT IGNORE INTO backfill_sources(catalog_entry,source_key,registry_json) VALUES(%s,%s,%s)',
            [(r['catalog_entry'], r['source_key'], canonical(r).decode()) for r in registry['sources']])
        rows = list(coverage(registry))
        cursor.executemany('INSERT IGNORE INTO backfill_coverage(cell_id,catalog_entry,coverage_year,coverage_json) VALUES(%s,%s,%s,%s)',
            [(job_id(r), r['catalog_entry'], r['year'], canonical(r).decode()) for r in rows])
    print(json.dumps({'catalog_entries': len(registry['sources']), 'coverage_cells': len(rows), 'verified_complete': 0}))


if __name__ == '__main__':
    main()
