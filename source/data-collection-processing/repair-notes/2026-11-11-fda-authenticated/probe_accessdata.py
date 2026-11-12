import json,time,requests
from urllib.parse import urlsplit
from pathlib import Path
from specialist_authenticated import credentials,table_rows
p=Path(__file__).parent;out=[]
for name,path,method in [('fda-productcodes','/rest/pcbapi/v1/industry/','GET'),('fda-enforcement','/rest/iresapi/recalls/','POST')]:
 user,key=credentials(name)
 for hostname,full in [('www.accessdata.fda.gov',False),('accessdata.fda.gov',False)]:
  time.sleep(1.1);headers={'Authorization-User':user,'Authorization-Key':key,'User-Agent':'Optima/1.0 (support@optima-holdings.com)','Accept':'application/json'};kwargs={}
  if method=='POST':kwargs['data']={'payload':json.dumps({'displaycolumns':'productid,recalleventid,recallnum,eventlmd,recallinitiationdt,productdescriptiontxt,productshortreasontxt,firmlegalnam,firmfeinum,centerclassificationtypetxt,enforcementreportdt','filter':json.dumps([{'eventlmdfrom':'10/28/2026'},{'eventlmdto':'10/28/2026'}]),'start':1,'rows':1,'sort':'productid','sortorder':'asc'})}
  try:
   r=requests.request(method,'https://'+hostname+path,params={'signature':str(int(time.time()*1000))},headers=headers,timeout=20,allow_redirects=False,**kwargs);item={'name':name,'host':hostname,'http_status':r.status_code,'redirect_path':urlsplit(r.headers.get('Location','')).path,'content_type':r.headers.get('Content-Type')}
   if r.status_code==200:
    d=r.json();item['api_code']=d.get('STATUSCODE',d.get('APIRETURNCODE'));item['message']=d.get('MESSAGE');rows=table_rows(d);item['fields']=list(rows[0])if rows else[]
  except Exception as e:item={'name':name,'host':hostname,'exception_type':type(e).__name__}
  out.append(item);print(item,flush=True)
(p/'accessdata-route-probes.json').write_text(json.dumps(out,indent=2))
