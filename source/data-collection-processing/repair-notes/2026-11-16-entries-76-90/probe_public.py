import json
from ops import remote,M7,session,B,BASE,P
code=r'''import json,requests,os,sys,re
from urllib.parse import urljoin
os.chdir('/opt/constellation/auxiliary-publication/source');sys.path.insert(0,os.getcwd())
from public_source_capture import Links
urls={
'ucdp':'https://ucdp.uu.se/downloads/',
'nhsbsa':'https://opendata.nhsbsa.net/api/3/action/package_show?id=english-prescribing-data-epd',
'nhsrows':'https://opendata.nhsbsa.net/api/3/action/datastore_search?resource_id=EPD_202401&limit=2',
'gba':'https://www.g-ba.de/bewertungsverfahren/nutzenbewertung/',
'has':'https://www.has-sante.fr/jcms/p_3546197/fr/open-data',
'openmedic':'https://www.data.gouv.fr/api/1/datasets/open-medic-base-complete-sur-les-depenses-de-medicaments-interregimes/',
'openmedic-ameli':'https://www.assurance-maladie.ameli.fr/etudes-et-donnees/open-medic-base-complete-depenses-medicaments',
'semi':'https://www.semi.org/en/news-resources/press',
'cadth':'https://www.cda-amc.ca/',
'cadth-pdf':'https://www.cda-amc.ca/sites/default/files/DRR/2024/SR0860_Patient_and_Clinician_Group_Input.pdf'}
out={}
for name,url in urls.items():
 try:
  r=requests.get(url,timeout=(10,30),headers={'User-Agent':'ConstellationResearch/1.0 (support@optima-holdings.com)'},allow_redirects=False);body=r.content;d={'url':url,'status':r.status_code,'media':r.headers.get('Content-Type'),'bytes':len(body),'location':r.headers.get('Location')}
  if r.status_code==200:
   if name in ('nhsbsa','nhsrows','openmedic'):
    d['json']=r.json()
   else:
    parser=Links();parser.feed(body.decode('utf8',errors='replace'));d['links']=[urljoin(url,x)for x in parser.links if any(word in x.lower()for word in ('csv','zip','.pdf','benefit','nutzenbewertung/','medicament','avis','commission','reimbursement','review','billings','equipment','ucdp','download','economic','wemi','category'))][:100]
  out[name]=d
 except Exception as error:out[name]={'error':type(error).__name__+':'+str(error)[:100]}
import boto3
key='research-data/constellation-backfill/repairs/entries-76-90-20261116/public-provider-probes.json';boto3.client('s3',region_name='us-east-1').put_object(Bucket='data-collection-059416028963-us-east-1-an',Key=key,Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps({'key':key}))
'''
r=remote(M7,code);raw=session.client('s3').get_object(Bucket=B,Key=json.loads(r['out'])['key'])['Body'].read();(P/'public-provider-probes.json').write_bytes(raw)
for name,d in json.loads(raw).items():
 summary={k:v for k,v in d.items()if k!='json'}
 if 'json'in d:
  v=d['json'];summary['keys']=list(v);data=v.get('result',v);summary['data_keys']=list(data)if isinstance(data,dict)else None
  if name=='nhsbsa':summary['resources']=[{k:r.get(k)for k in ['name','id','format','url','size']}for r in data.get('resources',[])][-4:]
  elif name=='nhsrows':summary['sample']=data
  else:summary['resources']=[{k:r.get(k)for k in ['title','format','url','filesize','id']}for r in v.get('resources',[])][:4]
 print(name,json.dumps(summary)[:6500])
