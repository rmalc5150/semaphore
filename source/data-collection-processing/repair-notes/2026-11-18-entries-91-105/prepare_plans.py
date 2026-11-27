import json
from pathlib import Path
from regional_source_review import PROFILES,PUBLIC_KEYS
from metadata_engine.source_policies import build
P=Path(__file__).parent;old={r['source']:r for r in json.load(open('config/constellation-public-sources.json'))['sources']}
seed={
91:['https://www.mhlw.go.jp/content/12400000/001492951.xlsx','https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00016.html','https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177182.html'],
93:['https://www.stats.gov.cn/english/PressRelease/202611/t20261117_1965883.html','https://www.stats.gov.cn/english/PressRelease/'],
94:['https://www.miit.gov.cn/gxsj/tjfx/dzxx/art/2026/art_bcb9e6c06d814f9183b9f5a795d0610e.html','https://www.miit.gov.cn/gxsj/tjfx/dzxx/index.html','https://www.miit.gov.cn/gxsj/tjfx/yclgy/index.html'],
95:['https://www.nea.gov.cn/20260825/1430d07985474c5b8110552785f1c74b/c.html','https://www.nea.gov.cn/'],
96:['https://www.nhsa.gov.cn/art/2026/11/14/art_53_23387.html','https://www.nhsa.gov.cn/col/col53/index.html'],
97:['https://www.mofcom.gov.cn/zcfb/zc/art/2026/art_531d1a665fab4dafb810927f37788e24.html','https://www.mofcom.gov.cn/zcfb/'],
100:['https://openapi.twse.com.tw/v1/opendata/t187ap03_L','https://openapi.twse.com.tw/v1/opendata/t187ap05_L'],
101:['https://opendata.customs.gov.tw/data/6053/csv.csv'],
102:['https://ibm.gov.in/IBMPortal/pages/monthly-statistics-of-mineral-production---2026'],
103:['https://geologi.esdm.go.id/publikasi/laporan-dan-buku/neraca-sumber-daya-dan-cadangan-mineral-batubara-dan-panas-bumi-indonesia-tahun-2026','https://geologi.esdm.go.id/publikasi/laporan-dan-buku/neraca-sumber-daya-dan-cadangan-mineral-batubara-dan-panas-bumi-indonesia-tahun-2025','https://geologi.esdm.go.id/publikasi/laporan-dan-buku'],
104:['https://dadosabertos.anm.gov.br/AMB/Producao_Bruta.csv','https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv','https://dadosabertos.anm.gov.br/AMB/Agua_Mineral_Producao.csv','https://www.gov.br/anm/pt-br/assuntos/economia-mineral/publicacoes/anuario-mineral/anuario-mineral'],
105:['https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_2022_2026.csv'],
}
updates={}
for source,p in PROFILES.items():
 n=p['entry']
 if source not in PUBLIC_KEYS:continue
 if n==92:
  updates[source]={**old[source],'enabled':False,'scope_note':'Discovery-only web route replaced by native CNINFO announcement index plus original PDF capture. Old receipts retained.'};continue
 note='Entire source-scoped native dataset/report/release with checksums; no complete historical coverage or unperformed numerical extraction asserted.'
 if n==91:note='Native published NDB aggregate workbooks and archives; suppressed cells retained. Not individual patient data or complete fiscal-year coverage.'
 if n in(93,94,95):note='Official statistical HTML releases and original same-release figures; numerical text retained, formal series extraction and complete history not asserted.'
 if n in(96,97):note='Original official notices and linked public documents; no clinical interpretation, current legal-effect conclusion or confidential reimbursement values inferred.'
 if n==100:note='Entire original TWSE issuer and monthly revenue rows; native units and reporting month retained. Current snapshots, not a complete MOPS filing archive or original historical vintages.'
 if n==101:note='Entire native monthly customs-clearance aggregate rows, with original reporting year and NTD-thousand units. Not detailed HS/country trade or original vintages.'
 if n==103:note='Official mineral/coal resource-and-reserve report PDFs, including their stated data cutoff; not unrelated energy-site images or complete historical vintages.'
 if n==104:note='Complete native AMB production CSV files and original yearbook PDFs; annual declared data and provider revisions, not original historical vintages.'
 if n==105:note='Complete native CFEM revenue CSV chunks, with original payment-period fields and encoding. Revenue collections; distribution/enforcement datasets and original historical vintages not inferred.'
 row={**old.get(source,{}),'catalog_entry':n,'source':source,'hosts':p['hosts'],'seeds':seed[n],'enabled':True,'raw_content_revision':'review-20261118','reviewed_document_discovery':True,'scope_note':note,'max_depth':3,'decodo':n in(94,95,96,97)}
 if n==102:row['historical_seeds']=['https://ibm.gov.in/IBMPortal/pages/monthly-statistics-of-mineral-production---'+str(y)for y in range(2026,2015,-1)]
 if n==105:row['historical_seeds']=['https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_'+years+'.csv'for years in ('2022_2026','2017_2021','2012_2016')]
 if n in (91,103,105):row['daily_execution']='worker'
 updates[source]=row
(P/'public-source-updates.json').write_text(json.dumps(updates,ensure_ascii=False,indent=2)+'\n')
native={
'cninfo_mainland_china_company_disclosures':{'source_id':'C092','source':'cninfo_mainland_china_company_disclosures','adapter':'additional_cninfo','api':'https://www.cninfo.com.cn/new/hisAnnouncement/query','enabled':True,'historical':True,'raw_content_revision':'original-documents-20261118','coverage_note':'Complete CNINFO announcement-index rows paired with original PDF filings, receipt identity and native China publication day; monthly bounded query scopes from 2016 and recent daily windows. No XBRL facts, complete market coverage or original historical vintages inferred.'},
'south_korea_fss_opendart':{'source_id':'C098','source':'south_korea_fss_opendart','adapter':'additional_dart','api':'https://opendart.fss.or.kr/api/list.json','enabled':True,'historical':True,'raw_content_revision':'original-documents-20261118','coverage_note':'Complete OpenDART filing-index rows paired with original XML ZIPs; receipt identities and all provider fields retained. Whole months require exhausted pagination; no XBRL fact extraction or original historical vintage asserted.'}}
(P/'native-source-updates.json').write_text(json.dumps(native,ensure_ascii=False,indent=2)+'\n')
worker_daily=[]
for source,row in updates.items():
 if row.get('daily_execution')!='worker':continue
 worker_daily.append({'unit':'constellation-public-daily-'+source+'.service','route_kind':'independent_public_daily','argv':['public_source_capture.py','--source',source,'--mode','daily','--limit','2'],'start_target':'2026-11-18','end_exclusive':'2026-11-19','cadence_seconds':21600,'timeout_seconds':900,'execution_enabled':False,'activation_staged':True,'remaining_requirements':['Worker deployment and raw/metadata proof required before activation'],'validation_basis':'Bounded daily native-file capture in the existing durable worker queue and shared lifecycle; no large downloads on t3','catalog_entry':row['catalog_entry']})
(P/'worker-daily-route-additions.json').write_text(json.dumps(worker_daily,indent=2)+'\n')
policies={k:v for k,v in build(Path.cwd()).items()if k in PUBLIC_KEYS|{'south_korea_fss_opendart'}};(P/'policies.json').write_text(json.dumps(policies,indent=2)+'\n')
print('Prepared',len(updates),'public source entries;',len(native),'native filing collectors;',len(policies),'contracts; KOSIS remains unconfigured.')
