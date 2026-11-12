"""Inspect processing state or explicitly resume a repaired source."""
import argparse,json
from pathlib import Path
from metadata_engine.runtime_db import Database,encoded


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['status','resume']);p.add_argument('--source');p.add_argument('--config',default=str(Path(__file__).resolve().parents[1]/'config/metadata-engine.json'));a=p.parse_args();db=Database(json.loads(Path(a.config).read_text()))
    if a.action=='resume':
        if not a.source:p.error('resume requires an explicit --source')
        with db.tx() as c:
            c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason=NULL,updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND state='raw_stopped'",(a.source,))
            c.execute("UPDATE engine_jobs SET state='queued',available_after=UTC_TIMESTAMP(6) WHERE source_key=%s AND state='raw_failed'",(a.source,))
    print(encoded(db.stats()))


if __name__=='__main__':main()
