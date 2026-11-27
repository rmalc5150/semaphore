from ops import *
from regional_source_review import Page,release_info
import re
s=session.client('s3');probes=json.loads((P/'provider-probes.json').read_text());out={}
lookup={v['entry']:v['source']for v in json.loads((P/'entries.json').read_text())};numbers={'mhlw':91,'nbs':93,'miit':94,'nea':95,'nhsa':96,'mofcom':97,'india':102}
for name in ['cninfo','mhlw','nbs','miit','nea','nhsa','mofcom','india','twse']:
 raw=s.get_object(Bucket=B,Key=probes[name]['body_key'])['Body'].read()
 try:
  v=json.loads(raw);out[name]={'type':type(v).__name__,'keys':list(v)[:15]if isinstance(v,dict)else None,'sample':v[:1]if isinstance(v,list)else v.get('announcements',[])[:2],'total':v.get('totalRecordNum')if isinstance(v,dict)else len(v)}
 except(ValueError,UnicodeDecodeError):
  page=Page(raw);out[name]={'title':page.headline,'content_head':page.content[:300],'regions':[(v['tag'],v['attrs'].get('id'),v['attrs'].get('class'),len(' '.join(v['parts'])))for v in page.regions],'subject_links':[(label[:90],u)for u,label in page.links(probes[name]['final_url'])if re.search(r'MSMP|monthly|NDB|第.{1,3}回|电力统计|药品目录|出口管制|下载|附件',label+u,re.I)][:60],'images':page.images[-6:],'release_info':release_info(lookup[numbers[name]],probes[name]['url'],raw)if name in numbers else None}
(P/'probe-details.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False)[:22000])
