"""Verify EIA access with two small requests; never log credential-bearing URLs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
import boto3

ROOT = Path(__file__).resolve().parent


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    config = json.loads((ROOT/'config/eia-access.json').read_text())
    report = {'checked_at':datetime.now(timezone.utc).isoformat(), 'secret_id':config['secret_id'],
              'checks':[], 'api_series_capture_started':False, 'historical_collection_complete':False}
    try:
        value=boto3.client('secretsmanager',region_name=config['region']).get_secret_value(SecretId=config['secret_id'])
        key=json.loads(value['SecretString'])[config['secret_field']]
        if not isinstance(key,str) or not key.strip():raise ValueError('invalid credential format')
        report['secret_readable']=True
        for label,dates in [('latest',{}),('january_2021',{'start':'2021-01','end':'2021-01'})]:
            params={'api_key':key.strip(),'frequency':'monthly','data[0]':'price',
                    'facets[stateid][]':'US','facets[sectorid][]':'ALL',
                    'sort[0][column]':'period','sort[0][direction]':'desc','length':1,'offset':0,**dates}
            request=Request(config['probe_endpoint']+'?'+urlencode(params),headers={'Accept':'application/json'})
            with build_opener(NoRedirect()).open(request,timeout=45) as response:
                raw=response.read(1024*1024+1); status=response.status
            if len(raw)>1024*1024:raise ValueError('response exceeds probe limit')
            data=json.loads(raw); rows=data.get('response',{}).get('data',[])
            valid=(not data.get('error') and len(rows)==1 and rows[0].get('stateid')=='US'
                   and rows[0].get('sectorid')=='ALL' and rows[0].get('price') is not None
                   and (label=='latest' or rows[0].get('period')=='2021-01'))
            # EIA responses echo request parameters, including authentication.
            # Persist only selected public fields, never the full response.
            report['checks'].append({'query':label,'http_status':status,'valid':bool(valid),
                'sample':{k:rows[0].get(k) for k in ('period','stateid','sectorid','price','price-units')} if rows else {},
                'response_sha256':hashlib.sha256(raw).hexdigest()})
        report['status']='verified_sample_access' if all(c['valid'] for c in report['checks']) else 'incomplete'
    except Exception as exc:
        report['status']='failed'; report['error_type']=type(exc).__name__
        if isinstance(exc,HTTPError):report['http_status']=exc.code;exc.close()
        if hasattr(exc,'response') and isinstance(exc.response,dict):
            report['aws_error_code']=exc.response.get('Error',{}).get('Code')
    (ROOT/'reports/eia-access-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return 0 if report['status']=='verified_sample_access' else 1


if __name__=='__main__':raise SystemExit(main())
