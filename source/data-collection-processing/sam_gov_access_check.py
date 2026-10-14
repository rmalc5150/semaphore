"""Two bounded SAM.gov access probes; never persist keys or response URLs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
import boto3

ROOT = Path(__file__).resolve().parent


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    config = json.loads((ROOT/'config/sam-gov-access.json').read_text())
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'secret_id':config['secret_id'],
              'checks':[], 'daily_capture_started':False, 'historical_collection_complete':False,
              'version_history_verified':False}
    try:
        secret = boto3.client('secretsmanager',region_name=config['region']).get_secret_value(SecretId=config['secret_id'])
        key = json.loads(secret['SecretString'])[config['secret_field']]
        if not isinstance(key,str) or not key.strip():
            raise ValueError('invalid credential format')
        report['secret_readable'] = True
        for start,end in [('10/09/2026','10/09/2026'),('01/01/2021','01/07/2021')]:
            params = {'postedFrom':start,'postedTo':end,'limit':1,'offset':0,'api_key':key.strip()}
            request = Request(config['endpoint']+'?'+urlencode(params),headers={'Accept':'application/json'})
            with build_opener(NoRedirect()).open(request,timeout=45) as response:
                raw = response.read(2*1024*1024+1)
                if len(raw)>2*1024*1024:
                    raise ValueError('response exceeds probe limit')
                status = response.status
            data = json.loads(raw)
            rows = data.get('opportunitiesData')
            total = data.get('totalRecords')
            valid = (isinstance(rows,list) and type(total) is int and total>=0
                     and len(rows)<=1 and all(isinstance(r,dict) and r.get('noticeId') for r in rows))
            # Response links may echo the key. Persist only a whitelisted summary.
            report['checks'].append({'posted_from':start,'posted_to':end,'http_status':status,
                'valid_response':bool(valid),'total_records':total if type(total) is int else None,
                'sample_count':len(rows) if isinstance(rows,list) else None,
                'response_sha256':hashlib.sha256(raw).hexdigest()})
            if not valid: break
            time.sleep(2)
        report['status'] = 'verified_sample_access' if len(report['checks'])==2 and all(
            c['valid_response'] and c['sample_count']>0 for c in report['checks']) else 'incomplete'
    except Exception as exc:
        report['status']='failed';report['error_type']=type(exc).__name__
        if isinstance(exc,HTTPError):
            report['http_status']=exc.code
            try:
                error=json.loads(exc.read(8192))
                if isinstance(error,dict):
                    report['provider_error']={k: str(error[k]).replace(key,'[REDACTED]')[:500]
                        for k in ('code','errorCode','message','errorMessage') if k in error and isinstance(error[k],(str,int))}
            except (ValueError,UnicodeDecodeError):
                pass
            finally:
                exc.close()
        if hasattr(exc,'response') and isinstance(exc.response,dict):
            report['aws_error_code']=exc.response.get('Error',{}).get('Code')
    (ROOT/'reports/sam-gov-access-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return 0 if report['status']=='verified_sample_access' else 1


if __name__=='__main__':raise SystemExit(main())
