#!/usr/bin/env python3
"""Corroborate candidate CIK and LEI identifiers against issuing registries."""
import argparse
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pyarrow.parquet as pq

from research_contract import load_json


USER_AGENT='Optima Holdings support@optima-holdings.com'


def normalize_name(value):
    value=re.sub(r'[^a-z0-9]+',' ',(value or '').casefold())
    value=re.sub(r'\bclass [a-z0-9]+ common stock\b|\bcommon stock\b|\b(?:adr|gdr|cedear)\b',' ',value)
    suffixes={'inc','incorporated','corp','corporation','company','co','ltd','limited','plc','sa','se','ag','nv','bv','llc'}
    words=value.split()
    while words and words[-1] in suffixes:words.pop()
    return ' '.join(words)


def similarity(a,b):return SequenceMatcher(None,normalize_name(a),normalize_name(b)).ratio()


def get_json(url,opener=urlopen):
    for attempt in range(4):
        try:
            with opener(Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/json'}),timeout=60) as response:
                raw=response.read(16*1024*1024+1)
            if len(raw)>16*1024*1024:raise ValueError('registry_response_too_large')
            return json.loads(raw),hashlib.sha256(raw).hexdigest()
        except HTTPError as exc:
            if exc.code==404:return None,None
            if exc.code not in (429,500,502,503,504):raise
        except (URLError,TimeoutError,json.JSONDecodeError):pass
        time.sleep(2**attempt)
    raise RuntimeError('registry_retries_exhausted')


def verify(eodhd_dir,review_dir,opener=urlopen):
    eodhd_dir=Path(eodhd_dir);review_dir=Path(review_dir);market=load_json(eodhd_dir/'release.json');review=load_json(review_dir/'release.json')
    profiles={r['provider_symbol']:r for r in pq.read_table(eodhd_dir/market['files']['company_profiles']['path']).to_pylist()}
    supported={r['provider_symbol'] for r in pq.read_table(review_dir/review['files']['sector_reviews']['path']).to_pylist() if r['review_status']=='supported'}
    sec,sec_hash=get_json('https://www.sec.gov/files/company_tickers_exchange.json',opener)
    sec_rows={str(row[0]).zfill(10):row for row in sec['data']}
    results=[];leis={profiles[s]['lei'] for s in supported if profiles[s].get('lei')}
    lei_rows={}
    for lei in sorted(leis):
        data,body_hash=get_json('https://api.gleif.org/api/v1/lei-records/'+lei,opener)
        if data:
            attrs=data['data']['attributes'];entity=attrs.get('entity') or {}
            legal=(entity.get('legalName') or {}).get('name')
            lei_rows[lei]={'name':legal,'status':attrs.get('registration',{}).get('status'),
                'entity_status':entity.get('status'),'sha256':body_hash}
        else:lei_rows[lei]=None
        time.sleep(.1)
    for symbol in sorted(supported):
        row=profiles[symbol];checks=[]
        raw_cik=(row.get('cik') or '').strip();cik=raw_cik.zfill(10) if raw_cik else ''
        if raw_cik:
            sec_row=sec_rows.get(cik);score=similarity(row['name'],sec_row[1]) if sec_row else 0
            checks.append({'system':'cik','value':cik,'registry':'sec_edgar','registry_name':sec_row[1] if sec_row else None,
                'name_similarity':round(score,4),'status':'verified' if sec_row and score>=.55 else 'name_mismatch' if sec_row else 'not_found',
                'source_url':'https://www.sec.gov/files/company_tickers_exchange.json','source_sha256':sec_hash})
        lei=row.get('lei')
        if lei:
            found=lei_rows.get(lei);score=similarity(row['name'],found['name']) if found else 0
            checks.append({'system':'lei','value':lei,'registry':'gleif','registry_name':found['name'] if found else None,
                'name_similarity':round(score,4),'registry_status':found['status'] if found else None,
                'entity_status':found['entity_status'] if found else None,
                'status':'verified' if found and score>=.55 else 'name_mismatch' if found else 'not_found',
                'source_url':'https://api.gleif.org/api/v1/lei-records/'+lei,'source_sha256':found['sha256'] if found else None})
        results.append({'provider_symbol':symbol,'profile_observation_id':row['observation_id'],'profile_name':row['name'],'checks':checks,
            'identity_status':'verified' if checks and all(c['status']=='verified' for c in checks) else
                              'name_mismatch' if any(c['status']=='name_mismatch' for c in checks) else 'unverified'})
    counts={}
    for row in results:counts[row['identity_status']]=counts.get(row['identity_status'],0)+1
    return {'version':'company-registry-verification-1.0','eodhd_release_id':market['release_id'],'review_release_id':review['release_id'],
        'method':'Exact identifier lookup with normalized-name similarity threshold 0.55. Identifier existence with a name mismatch remains unresolved.',
        'counts':counts,'records':results}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--eodhd-release',type=Path,required=True);p.add_argument('--review-release',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    value=verify(a.eodhd_release,a.review_release);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');print(json.dumps(value['counts']))


if __name__=='__main__':main()
