from pathlib import Path
import json,os
roots=list(Path('/home/ec2-user/data-collection-processing/constellation/daily-workspaces').glob('*'));changed=[]
for root in roots:
 cfg=root/'config/pdf-proxy-fallback.json'
 if not cfg.exists()or not json.loads(cfg.read_text()).get('enabled'):continue
 p=root/'regulatory_collection.py';s=p.read_text()
 if "get('last_http_status') != 429"not in s:
  s=s.replace('            if candidate:\n                from pdf_proxy_fallback',"            if candidate and (exc.diagnostics or {}).get('last_http_status') != 429:\n                from pdf_proxy_fallback",1)
  a=s.index('    def _get_direct(');z=s.index('    def json(',a);block=s[a:z]
  block=block.replace('        for attempt in range(4):','        last_http_status = None\n        for attempt in range(4):',1).replace('            except HTTPError as exc:','            except HTTPError as exc:\n                last_http_status = exc.code',1).replace('            except (URLError, TimeoutError):','            except (URLError, TimeoutError):\n                last_http_status = None',1).replace('raise SourceIssue("source_retries_exhausted", True)','raise SourceIssue("source_retries_exhausted", True, {"last_http_status": last_http_status})',1)
  s=s[:a]+block+s[z:];compile(s,str(p),'exec');tmp=p.with_suffix('.transport.tmp');tmp.write_text(s);os.chmod(tmp,0o644);tmp.replace(p);changed.append(str(p))
 p=root/'public_source_capture.py'
 if p.exists():
  s=p.read_text();needle="            if not source.get('decodo'):raise"
  if needle in s:
   s=s.replace(needle,"            if not source.get('decodo'):\n                from pdf_proxy_fallback import settings as pdf_settings, eligible as pdf_eligible\n                cfg=pdf_settings()\n                if not (cfg.get('enabled') and source['source'] in cfg.get('allowed_sources',[]) and pdf_eligible(url,'source_retries_exhausted')):raise",1);compile(s,str(p),'exec');tmp=p.with_suffix('.transport.tmp');tmp.write_text(s);os.chmod(tmp,0o644);tmp.replace(p);changed.append(str(p))
print(json.dumps({'changed_files':len(changed)}))
