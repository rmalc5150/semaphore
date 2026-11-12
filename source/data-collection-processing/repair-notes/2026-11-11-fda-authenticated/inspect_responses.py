import json,boto3,requests,re
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an'
for folder in p.iterdir():
 if not folder.is_dir()or not(folder/'sample-record.json').exists():continue
 r=json.loads((folder/'sample-record.json').read_text());ref=r['payload']['source_evidence'][0];raw=s.get_object(Bucket=bucket,Key='research-data/'+ref['key'])['Body'].read();(folder/'sample-response.json').write_bytes(raw);o=json.loads(raw);summary={k:(v if not isinstance(v,(dict,list))else('list:'+str(len(v))if isinstance(v,list)else list(v)))for k,v in o.items()};print(folder.name,summary)
for url in ('https://www.accessdata.fda.gov/scripts/ires/apidocs/','https://www.accessdata.fda.gov/scripts/ora/pcb/apidocs/'):
 html=requests.get(url,timeout=20).text;print('DOC_LINKS',url,re.findall(r'(?:src|url)\s*[:=]\s*[\'\"]([^\'\"]+)',html)[-20:]);(p/('ires-doc.html'if'ires/'in url else'pcb-doc.html')).write_text(html)
