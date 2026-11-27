import json
from ops import remote,M7,P
r=remote(M7,r'''import os,sys,requests,json
os.chdir('/opt/constellation/auxiliary-publication/source');sys.path.insert(0,os.getcwd())
import re
from public_source_capture import Links
url='https://open-data-assurance-maladie.ameli.fr/medicaments/download.php?Dir_Rep=Open_MEDIC_Base_Complete&Annee=2025';r=requests.get(url,timeout=30);body=r.text;parser=Links();parser.feed(body);out={'forms':re.findall(r'<form.*?</form>',body,re.S),'links':parser.links,'scripts':re.findall(r'<script[^>]*>(.*?)</script>',body,re.S)}
from decodo_scraping_api import scrape,cached_token
try:
 result=scrape('https://www.semi.org/en/news-resources/press',cached_token(),parameters={'headless':'html'},timeout=70);out['semi_gateway']={'keys':list(result),'rows':[{k:(len(v)if k=='content'and isinstance(v,str)else v)for k,v in row.items()if k in ('status_code','content','encoding','content_encoding','task_id')}for row in result['results']]}
except Exception as e:out['semi_gateway']={'error':str(e)}
print(json.dumps(out))
''');(P/'medic-forms.json').write_text(r['out']);print(r['out'][:9000])
