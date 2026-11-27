import os,sys,json
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings
from specialist_inputs import SpecialistClient
from additional_source_apis import get_json
c=SpecialistClient(StorageSettings.load(root/'config/collection-storage.s3.json').store(),'wto_timeseries_api')
for period in ('2016','default'):
 try:
  d,_=get_json(c,'https://api.wto.org/timeseries/v1/data',{'i':'TP_B_0180','r':'all','p':'default','ps':'default','pc':'default','fmt':'json','mode':'codes','max':500,'off':0,'head':'M','lang':1,'meta':'true','ps':period},'WTO-primary',key_header='Ocp-Apim-Subscription-Key',allow_empty=True);print(json.dumps({'period':period,'shape':list(d)if isinstance(d,dict)else None,'rows':len(d.get('Dataset',[]))if d else None,'evidence':c.evidence[-1:]}))
 except Exception as e:
  print(json.dumps({'period':period,'reason':getattr(e,'code',None),'diagnostics':getattr(e,'diagnostics',None),'evidence':c.evidence[-1:]}))
  if c.evidence:
   r=c.store.get(c.evidence[-1]['key']);print('PROVIDER_ERROR',r.body.decode(errors='replace')[:1800])
