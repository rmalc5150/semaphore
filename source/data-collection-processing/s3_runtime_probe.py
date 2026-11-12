"""Smoke-test real service isolation, S3 recovery and Parquet-in-RAM output."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import pyarrow as pa
import pyarrow.parquet as pq
from research_contract import ROOT, load_json

assert os.environ.get('OPTIMA_S3_RUNTIME_ACTIVE') == '1'
for path in (Path('/home/ec2-user/.s3-runtime-disk-probe'), Path('/tmp/s3-runtime-disk-probe')):
    try:
        path.write_text('disk writes must fail')
    except PermissionError:
        pass
    except OSError as exc:
        assert exc.errno == 30, exc
    else:
        raise AssertionError('Disk write was permitted: ' + str(path))
universe = load_json(ROOT / 'config/company-universe.v0.1.json')
assert universe['universe_version']
path = ROOT / 'reports/s3-runtime-probe.sqlite3'
with closing(sqlite3.connect(path)) as db:
    db.execute('CREATE TABLE IF NOT EXISTS runs (n INTEGER)')
    db.execute('INSERT INTO runs VALUES (1)')
    db.commit()
    count = db.execute('SELECT count(*) FROM runs').fetchone()[0]
output = ROOT / 'athena-pilot-build/s3-runtime-probe/part.parquet'
output.parent.mkdir(parents=True, exist_ok=True)
pq.write_table(pa.table({'runs': [count]}), output)
assert output.resolve().is_relative_to('/dev/shm/optima-s3')
report = {'probe_runs': count, 'source_universe': universe['universe_version'],
          'disk_writes_blocked': True, 'parquet_workspace': 'ram', 'sqlite_workspace': 'ram'}
(ROOT / 'reports/s3-runtime-probe.json').write_text(json.dumps(report))
print(json.dumps(report), flush=True)
