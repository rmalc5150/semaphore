#!/usr/bin/env python3
"""Curate completed market windows with source evidence and explicit limitations."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from collection_storage import StorageSettings
from regulatory_athena import read_inputs
from research_contract import ROOT,canonical_json,digest,load_json
import sec_athena_pilot as release
from window_publication import publish_pending

COMMON=[(n,'string') for n in ('record_id','observation_id','source','symbol','event_date','ingested_at','source_url','data_json','record_json')]+[('candidate_listing_ids','array<string>'),('point_in_time_eligible','boolean')]
SCHEMAS={'market_prices':COMMON+[(n,'string') for n in ('currency','open','high','low','close','adjusted_close','volume')],
 'corporate_actions':COMMON+[(n,'string') for n in ('kind','amount','currency','split_numerator','split_denominator','share_multiplier')],
 'market_coverage':[(n,'string') for n in ('source_manifest','source','window_start','window_end_exclusive','mode','scope_json','coverage_note')]+[('records','bigint')]}


def prepare(store,settings,config,keys,output_root):
    entries,universe,inputs=read_inputs(store,keys,allowed={'hkex_prices','eodhd_market'},dataset='market_records')
    tables={n:[] for n in SCHEMAS}
    for oid,entry in sorted(entries.items()):
        r=entry['record']; p=r['payload'];d=p['data']
        common={'record_id':r['record_id'],'observation_id':oid,'source':r['source'],'symbol':p['symbol'],
            'event_date':d['date'],'ingested_at':r['ingested_at'],'source_url':r['source_url'],
            'data_json':release.json_text(d),'record_json':release.json_text(r),
            'candidate_listing_ids':p['candidate_listing_ids'],'point_in_time_eligible':False}
        if p['kind']=='prices':
            tables['market_prices'].append({**common,**{k:None if d.get(k) is None else str(d[k]) for k in ('currency','open','high','low','close','adjusted_close','volume')}})
        else:
            tables['corporate_actions'].append({**common,'kind':p['kind'],'amount':d.get('value'),'currency':d.get('currency'),
                'split_numerator':d.get('numerator'),'split_denominator':d.get('denominator'),'share_multiplier':d.get('share_multiplier')})
    for key in sorted(set(keys)):
        m=json.loads(release.get_bytes(store,key));t=m['task']
        tables['market_coverage'].append({'source_manifest':key,'source':t['source'],'window_start':t['window']['start'],
          'window_end_exclusive':t['window']['end'],'mode':t['mode'],'scope_json':release.json_text(t['scope']),'records':m['record_count'],
          'coverage_note':'Complete specified source request only; current listing identity and adjusted history are not point-in-time verified. HKEX quotations do not supply corporate actions or opening/adjusted prices. EODHD corporate-action scope is splits and dividends.'})
    identity=digest({'version':'market-athena-1.0','inputs':inputs,'config':config,'schemas':SCHEMAS,'arrow':pa.__version__})
    root=Path(output_root)/identity;prefix=config['curated_prefix']+'/'+identity;files={};ddl=[]
    for name,rows in tables.items():
        table=pa.Table.from_pylist(rows,schema=pa.schema([(n,release.ARROW_TYPES[t]) for n,t in SCHEMAS[name]]))
        relative='tables/'+name+'/part-00000.parquet';path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        pq.write_table(table,path,compression='snappy');release.require(pq.ParquetFile(path).read().equals(table),'Market Parquet roundtrip mismatch')
        body=path.read_bytes();location=f's3://{settings.s3_bucket}/{settings.s3_prefix}/{prefix}/tables/{name}/'
        files[name]={'path':relative,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'rows':len(rows),'location':location,'columns':SCHEMAS[name]}
        ddl.append(f"CREATE EXTERNAL TABLE {config['database']}.{name} ("+', '.join(f'{n} {t}' for n,t in SCHEMAS[name])+f") STORED AS PARQUET LOCATION '{location}';")
    report={'curator_version':'market-athena-1.0','catalog_owner':'market','workgroup_description':'Optima market pilot',
       'release_id':identity,'release_prefix':prefix,'bucket':settings.s3_bucket,'s3_prefix':settings.s3_prefix,
       'config':config,'inputs':inputs,'universe_hash':digest(universe),'files':files,'queries':{},'expected_results':{},'status':'locally_validated'}
    (root/'release.json').write_bytes(canonical_json(report)+b'\n');(root/'tables.sql').write_text('\n'.join(ddl));(root/'queries.sql').write_text('')
    return root


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--max-windows',type=int,default=24);args=parser.parse_args()
    if not 1<=args.max_windows<=24:parser.error('--max-windows must be 1..24')
    with (ROOT/'.market-athena.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json')
        result=publish_pending(settings.store(),settings,'market',load_json(ROOT/'config/market-athena.json'),prepare,ROOT/'market-athena-build',args.max_windows)
        print(json.dumps(result),flush=True);return 1 if result['status']=='failed' else 0

if __name__=='__main__':raise SystemExit(main())
