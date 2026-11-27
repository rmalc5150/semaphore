"""Validate representative native inputs through the deployed worker runtime."""
from datetime import date
import json
import os

import boto3
import public_source_capture as capture
from metadata_engine.evidence import evidence_for
from metadata_engine.streaming import session as streaming
from metadata_engine.worker import load_input
from trade_mining_sources import COCHILCO, SERNAGEOMIN, SNIFA, MINEM, SIACAM, SIGMINE, request_seeds

B = 'data-collection-059416028963-us-east-1-an'
BASE = 'research-data/constellation-backfill/repairs/entries-106-120-20261120/'
s3 = boto3.client('s3',region_name='us-east-1')


def get(name):
    return json.loads(s3.get_object(Bucket=B, Key=BASE+name)['Body'].read())


def save(name, data):
    s3.put_object(Bucket=B, Key=BASE+name, Body=json.dumps(data,ensure_ascii=False).encode(), ServerSideEncryption='AES256')


def main():
    updates, policies = get('capture-updates.json'), get('policies.json')
    staged = get('staged-raw-proof.json')
    out = {}
    need_originals = {COCHILCO,SERNAGEOMIN,SNIFA,MINEM,SIGMINE}
    for source, spec in updates.items():
        result = {}
        for mode in ('daily','historical'):
            options = [v for v in staged.get(source,{}).get(mode,[]) if v['state']=='validated_raw']
            if source in need_originals:
                seeds = request_seeds(source,mode,date.today().isoformat())
                seeds = seeds or spec.get('historical_seeds' if mode=='historical' else 'seeds') or spec['seeds']
                for url in seeds[:2] if source==SIGMINE else seeds[:1]:
                    try:
                        row,_=capture.capture(s3,spec,{'url':url,'depth':0},mode,publish_receipt=False)
                        if row['artifact_kind'] != 'public_document':
                            raise ValueError('expected_original_document')
                        key=BASE+'staged-receipts/'+mode+'/'+source+'/'+row['sha256']+'.jsonl'
                        capture.put(s3,key,capture.encode(row),'application/x-ndjson')
                        options.append({'receipt_key':key})
                    except Exception as error:
                        result.setdefault('errors',[]).append({'mode':mode,'url':url,'error':type(error).__name__+': '+str(error)[:200]})
            checks, seen = [], set()
            for option in reversed(options):
                key = option['receipt_key']
                if key in seen:
                    continue
                seen.add(key)
                try:
                    rows,_,manifest=load_input(s3,B,{'input_format':'public_receipt','input_key':key,'contract_version':'2.0.3'})
                    assert rows and manifest['task']['mode']==mode
                    with streaming():
                        evidence=[evidence_for(row,policies[source],s3,B)[0] for row in rows]
                    checks.append({'key':key,'rows':len(rows),'original':evidence[0]})
                except Exception as error:
                    result.setdefault('errors',[]).append({'mode':mode,'key':key,'error':type(error).__name__+': '+str(error)[:200]})
            result[mode]=checks
        result['validated_both_modes']=bool(result['daily'] and result['historical'])
        # Different files prove historical editions of annual and monthly publications.
        if source in (COCHILCO,SERNAGEOMIN,MINEM):
            result['validated_both_modes'] = result['validated_both_modes'] and (
                result['daily'][0]['original']['sha256'] != result['historical'][0]['original']['sha256']
            )
        out[source]=result
        save('worker-raw-proof.json',{'sources':out,'finished':False})
        print(source,result['validated_both_modes'],flush=True)
    census='us_census_international_trade_api'
    selected=get('census-proof.json')
    result={}
    for mode in ('daily','historical'):
        checks=[]
        for item in [v for v in selected if v.get('mode')==mode and v['status']=='verified'][:2]:
            rows,_,_=load_input(s3,B,{'input_format':'legacy_batch','input_key':item['key']})
            artifacts=[evidence_for(row,policies[census],s3,B)[0] for row in rows]
            checks.append({'key':item['key'],'rows':len(rows),'original':artifacts[0]})
        result[mode]=checks
    result['validated_both_modes']=bool(result['daily'] and result['historical'])
    out[census]=result
    save('worker-raw-proof.json',{'sources':out,'finished':True})


if __name__=='__main__':
    main()
