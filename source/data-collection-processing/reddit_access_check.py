"""One application-only OAuth check; no posts, account actions, or saved tokens."""
import base64
from datetime import datetime, timezone
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
    config = json.loads((ROOT/'config/reddit-access.json').read_text())
    report = {'checked_at':datetime.now(timezone.utc).isoformat(), 'secret_id':config['secret_id'],
              'authentication_verified':False, 'collection_enabled':False,
              'commercial_approval_verified':False, 'historical_access_verified':False}
    try:
        response = boto3.client('secretsmanager',region_name=config['region']).get_secret_value(SecretId=config['secret_id'])
        secret = json.loads(response['SecretString'])
        client_id, client_secret = (secret[config[field]] for field in ('client_id_field','client_secret_field'))
        if not all(isinstance(value,str) and value.strip() for value in (client_id,client_secret)):
            raise ValueError('missing credential fields')
        report['secret_readable']=True
        auth=base64.b64encode((client_id.strip()+':'+client_secret.strip()).encode()).decode()
        request=Request(config['token_endpoint'],data=urlencode({'grant_type':'client_credentials'}).encode(),
            headers={'Authorization':'Basic '+auth,'User-Agent':config['user_agent'],
                     'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json'})
        with build_opener(NoRedirect()).open(request,timeout=45) as response:
            report['http_status']=response.status
            body=response.read(65537)
        if len(body)>65536:raise ValueError('response exceeds limit')
        payload=json.loads(body)
        report['authentication_verified']=bool(isinstance(payload.get('access_token'),str)
            and payload['access_token'] and str(payload.get('token_type','')).lower()=='bearer')
        report['status']='authentication_verified' if report['authentication_verified'] else 'authentication_unverified'
        if payload.get('error') in ('invalid_client','invalid_grant','unauthorized_client','unsupported_grant_type','invalid_request'):
            report['oauth_error']=payload['error']
    except Exception as exc:
        report['status']='failed'; report['error_type']=type(exc).__name__
        if isinstance(exc,HTTPError):
            report['http_status']=exc.code
            try:
                error=json.loads(exc.read(65536)).get('error')
                if error in ('invalid_client','invalid_grant','unauthorized_client','unsupported_grant_type','invalid_request'):
                    report['oauth_error']=error
            except (ValueError,AttributeError):pass
            finally:exc.close()
        if hasattr(exc,'response') and isinstance(exc.response,dict):
            report['aws_error_code']=exc.response.get('Error',{}).get('Code')
    (ROOT/'reports/reddit-access-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return 0 if report['authentication_verified'] else 1


if __name__=='__main__':raise SystemExit(main())
