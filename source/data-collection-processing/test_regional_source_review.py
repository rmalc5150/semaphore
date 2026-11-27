import io,json,hashlib,tempfile,unittest,struct,zlib
from pathlib import Path
from unittest.mock import Mock,patch
from regional_source_review import in_scope,release_info,discover,figure_urls,PROFILES
from metadata_engine.regional_public import customs_decoded,customs_rows,twse_rows,validate_figure
from metadata_engine.evidence import RawFailure

class RegionalSources(unittest.TestCase):
 def test_navigation_is_not_statistical_release(self):
  html=b'<html><title>Latest Releases</title><nav>Industrial Production 2026 2025 10 20</nav><p>Index only</p></html>'
  self.assertIsNone(release_info('china_nbs_industrial_production','https://www.stats.gov.cn/english/PressRelease/202611/t20261117_1965883.html',html))
 def test_short_official_nea_release_is_substantive(self):
  source='china_nea_power_statistics';html=('<h1>国家能源局发布2026年1-7月份全国电力统计数据</h1><div class="article-content">全国装机容量40.8亿千瓦，增长11.0%。太阳能12.9亿千瓦增长16.1%，风电6.9亿千瓦增长19.5%。'+('完整原始统计说明。'*12)+'</div>').encode()
  info=release_info(source,'https://www.nea.gov.cn/20260825/1430d07985474c5b8110552785f1c74b/c.html',html);self.assertEqual(info['kind'],'official_release')
 def test_export_control_menu_cannot_become_law(self):
  body=('<title>中国出口管制信息网</title><h3>两用物项和技术进出口审批</h3><p>'+('2026 10 50 出口管制 菜单 '*60)+'</p>').encode()
  self.assertIsNone(release_info('china_mofcom_export_controls','https://exportcontrol.mofcom.gov.cn/article/zcfg/gnzcfg/zcfggzqd/202610/1322.html',body))
 def test_mofcom_formal_title_and_native_release(self):
  body=('<meta name="ArticleTitle" content="商务部2026年第52号出口管制公告"><p>'+('真实两用物项出口管制通知2026年10月19日；'*12)+'</p>').encode();self.assertIsNotNone(release_info('china_mofcom_export_controls','https://www.mofcom.gov.cn/zcfb/zc/art/2026/art_531d1a665fab4dafb810927f37788e24.html',body))
 def test_mhlw_discovers_dataset_not_faq_pdf(self):
  source={'source':'japan_mhlw_ndb_open_data'};body=b'<a href="/content/12400000/data.xlsx">Data</a><a href="/content/12400000/faq.pdf">FAQ</a>'
  self.assertEqual(discover(body,'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00016.html',source,1),[{'url':'https://www.mhlw.go.jp/content/12400000/data.xlsx','depth':2}])
 def test_discovery_deduplicates_and_ignores_fragments(self):
  source={'source':'india_ibm_mineral_production'};url='https://ibm.gov.in/IBMPortal/pages/monthly-statistics-of-mineral-production---2026';body=b'<a href="#main">Skip</a><a href="/writereaddata/files/MSMP_JAN_2026.pdf">January</a><a href="/writereaddata/files/MSMP_JAN_2026.pdf">Again</a>'
  self.assertEqual(len(discover(body,url,source,0)),1)
 def test_nhsa_site_navigation_does_not_expand_to_unrelated_columns(self):
  body=b'<a href="/col/col51/index.html">Other navigation</a><a href="/col/col53/index.html">Policies</a>'
  rows=discover(body,'https://www.nhsa.gov.cn/art/2026/11/14/art_53_23387.html',{'source':'china_nhsa_reimbursement_and_procurement'},0)
  self.assertEqual([r['url']for r in rows],['https://www.nhsa.gov.cn/col/col53/index.html'])
 def test_anm_bare_contact_email_is_not_an_archive_link(self):
  source='brazil_anm_mineral_yearbook';base='https://www.gov.br/anm/pt-br/assuntos/economia-mineral/publicacoes/anuario-mineral/'
  self.assertFalse(in_scope(base+'biblioteca@anm.gov.br',source,True));self.assertTrue(in_scope(base+'report@author.pdf',source))
 def test_scope_rejects_wrong_provider_and_images(self):
  self.assertFalse(in_scope('https://evil.example/content/a.xlsx','japan_mhlw_ndb_open_data'));self.assertFalse(in_scope('https://www.esdm.go.id/logo.jpeg','indonesia_esdm_and_geological_agency_mineral_statistics'))
 def test_same_release_figures_exclude_site_logo(self):
  body=b'<h1>Release</h1><img src="chart.png"><img src="/images/logo.png">';url='https://www.nea.gov.cn/20260825/abc/c.html';self.assertEqual(figure_urls(url,body),['https://www.nea.gov.cn/20260825/abc/chart.png'])
 def test_corrupt_png_crc_rejected(self):
  with self.assertRaises(RawFailure):validate_figure(b'\x89PNG\r\n\x1a\n'+b'\0'*20)
 def test_png_end_marker_without_image_cannot_pass(self):
  chunk=b'IEND';raw=b'\x89PNG\r\n\x1a\n'+struct.pack('>I',0)+chunk+struct.pack('>I',zlib.crc32(chunk))
  with self.assertRaises(RawFailure):validate_figure(raw)
 def test_native_customs_year_units_and_zero_are_retained(self):
  raw='年度,月份,出口總值(新臺幣千元),進口總值(新臺幣千元),備註\r\n115,9,0,21,原值\r\n'.encode('utf-8-sig');r=customs_decoded(raw)[0];self.assertEqual(r['年度'],'115');self.assertEqual(r['出口總值(新臺幣千元)'],'0');self.assertEqual(r['備註'],'原值')
 def test_customs_bad_width_cannot_pass(self):
  raw='年度,月份,出口總值(新臺幣千元),進口總值(新臺幣千元)\n115,9,2,4,unexpected\n'.encode()
  with self.assertRaises(RawFailure):customs_decoded(raw)
 def test_twse_original_rows_not_file_count_and_keep_all_fields(self):
  source='taiwan_twse_mops_issuer_and_revenue_archives';rows=[{'公司代號':'1101','公司名稱':'台泥','資料年月':'11510','營業收入-當月營收':'0','備註':'unchanged'}];body=json.dumps(rows).encode();sha=hashlib.sha256(body).hexdigest();receipt={'source':source,'source_url':'https://openapi.twse.com.tw/v1/opendata/t187ap05_L','artifact_uri':'s3://b/raw','sha256':sha,'retrieved_at':'2026-11-18T00:00:00Z'}
  with patch('metadata_engine.regional_public.object_bytes',return_value=body):result=twse_rows(receipt,Mock(),'b')
  self.assertEqual(result[0]['payload']['data'],rows[0]);self.assertEqual(result[0]['source_record_id'],'1101:11510');self.assertEqual(result[0]['dataset'],'twse_monthly_revenue')
 def test_anm_ca_is_scoped_to_one_provider(self):
  from provider_tls import ca_bundle_for
  self.assertIs(ca_bundle_for('https://www.stats.gov.cn/'),True);path=ca_bundle_for('https://dadosabertos.anm.gov.br/AMB/');self.assertTrue(Path(path).read_bytes().endswith(Path('config/anm-intermediate.pem').read_bytes()))


class FilingCapture(unittest.TestCase):
 def test_cninfo_uses_china_date_and_keeps_cached_index(self):
  from filing_originals_capture import fetch
  from specialist_inputs import item
  from types import SimpleNamespace
  from datetime import datetime
  from zoneinfo import ZoneInfo
  filing={'announcementId':'1225676806','announcementTime':int(datetime(2026,11,17,0,0,tzinfo=ZoneInfo('Asia/Shanghai')).timestamp()*1000),'adjunctUrl':'finalpage/2026-11-17/1225676806.PDF','secCode':'300748','extra':'retain'}
  second={**filing,'announcementId':'1225676807','adjunctUrl':'finalpage/2026-11-17/1225676807.PDF'};raw=json.dumps({'announcements':[filing,second],'totalRecordNum':2,'totalpages':1}).encode();ref={'key':'source_documents/x','sha256':hashlib.sha256(raw).hexdigest(),'source_url':'https://www.cninfo.com.cn/new/hisAnnouncement/query'};client=SimpleNamespace(evidence=[],store=Mock());client.store.get.return_value=SimpleNamespace(body=raw);job={'source':'cninfo_mainland_china_company_disclosures','parameters':{},'start':'2026-11-17','end':'2026-11-18'}
  with patch('filing_originals_capture.request',return_value=(raw,ref))as request,patch('filing_originals_capture.original',return_value=({'source_url':'https://static.cninfo.com.cn/finalpage/2026-11-17/1225676806.PDF'},None)):
   rows,cursor=fetch(client,job,None,item);self.assertEqual(rows[0]['date'],'2026-11-17');self.assertEqual(rows[0]['data']['filing'],filing)
   rows,done=fetch(client,job,cursor,item);self.assertIsNone(done);self.assertEqual(request.call_count,1);self.assertEqual(rows[0]['id'],'1225676807')

class FilingValidation(unittest.TestCase):
 def test_dart_viewer_keeps_same_receipt_documents(self):
  from metadata_engine.dart_originals import parse_view
  receipt = '20250701000017'
  source = {'corp_name':'하나자산운용','report_nm':'[기재정정]투자설명서(집합투자증권)(펀드이름)'}
  viewer = f"""<title>하나자산운용/투자설명서(집합투자증권)/2025.07.01</title>
    <select id="family"><option selected value="rcpNo={receipt}" title="투자설명서(집합투자증권)"></option></select>
    <select id="att">
      <option value="rcpNo={receipt}&amp;dcmNo=10706856"></option>
      <option value="rcpNo=20250328000519&amp;dcmNo=10470145"></option>
    </select>
    <button class="btnDown" onclick="openPdfDownload('{receipt}', '10706855');"></button>"""
  self.assertEqual(parse_view(viewer.encode(),receipt,source),['10706855','10706856'])
  with self.assertRaisesRegex(RawFailure,'attachment_identity_mismatch'):
   parse_view(viewer.replace('10470145','other').encode(),receipt,source)
  with self.assertRaisesRegex(RawFailure,'document_identity_missing'):
   parse_view(viewer.replace(f"('{receipt}'","('20250328000519'").encode(),receipt,source)

 def test_dart_missing_archive_repair_remains_bound_to_native_index(self):
  from metadata_engine.regional_filings import evidence
  receipt = '20261105000526'
  filing = {'rcept_no':receipt,'corp_name':'Original'}
  raw = json.dumps({'list':[filing]}).encode()
  sha = hashlib.sha256(raw).hexdigest()
  record = {'source':'south_korea_fss_opendart','source_record_id':receipt,
            'payload':{'data':{'filing':filing,'primary_document':None,'index_evidence':{
             'key':'source_documents/index','sha256':sha,'source_url':'https://opendart.fss.or.kr/api/list.json'}}}}
  original = {'artifact_kind':'primary_document','s3_uri':'s3://b/verified.pdf'}
  s3 = Mock()
  with patch('metadata_engine.regional_filings.object_bytes',return_value=raw), \
       patch('metadata_engine.dart_originals.repaired_artifacts',return_value=[original]) as repaired:
   self.assertEqual(evidence(record,s3,'b')[-1],original)
   repaired.assert_called_once_with(s3,'b',receipt,filing,sha,anchor='archived_index')

 def test_dart_strict_legacy_xml_fallback(self):
  from metadata_engine.regional_filings import dart_xml_encoding
  content = '원본 공시 자료입니다. ' * 20
  wrapped = '<?xml version="1.0" encoding="UTF-8"?><DOCUMENT>' + content + '</DOCUMENT>'
  self.assertIsNone(dart_xml_encoding(wrapped.encode('utf-8')))
  self.assertEqual(dart_xml_encoding(wrapped.encode('euc-kr')), 'euc-kr')
  extended = wrapped.replace(content, '똠' + content)
  self.assertEqual(dart_xml_encoding(extended.encode('cp949')), 'cp949')
  for broken in (wrapped.replace('</DOCUMENT>', '</OTHER>'), wrapped.replace(content, content + '&cr;')):
   with self.assertRaisesRegex(RawFailure, 'dart_original_xml_invalid'):
    dart_xml_encoding(broken.encode('euc-kr'))

 def test_changed_index_row_cannot_pass_with_matching_receipt_id(self):
  from metadata_engine.regional_filings import evidence
  row={'rcept_no':'20261105000526','corp_name':'Original'};raw=json.dumps({'list':[row]}).encode();bad={**row,'corp_name':'Changed'};record={'source':'south_korea_fss_opendart','source_record_id':row['rcept_no'],'payload':{'data':{'filing':bad,'primary_document':{'source_url':'https://opendart.fss.or.kr/api/document.xml?rcept_no='+row['rcept_no']},'index_evidence':{'key':'source_documents/index','sha256':hashlib.sha256(raw).hexdigest(),'source_url':'https://opendart.fss.or.kr/api/list.json'}}}}
  with patch('metadata_engine.regional_filings.object_bytes',return_value=raw),self.assertRaisesRegex(RawFailure,'entire_native_row_mismatch'):evidence(record,Mock(),'b')

class ANMEncoding(unittest.TestCase):
 def test_native_portuguese_legacy_encoding_and_decimal_strings(self):
  from metadata_engine.regional_public import validate_anm_csv
  with tempfile.TemporaryDirectory()as tmp:
   p=Path(tmp)/'cfem.csv';p.write_bytes('"Ano","Mês","Processo","ValorRecolhido"\n"2026","9","12345","12,34"\n'.encode('cp1252'));entry={'path':p};validate_anm_csv(entry,'brazil_anm_cfem_mining_royalties');self.assertEqual(entry['validation']['encoding'],'cp1252');self.assertEqual(entry['validation']['rows'],1)


class StagedCapture(unittest.TestCase):
 def test_transient_failure_can_resume_today_without_losing_frontier(self):
  from public_source_capture import run
  from datetime import datetime,timezone
  import requests
  source={'source':'fixture','catalog_entry':999,'hosts':['official.example'],'scope_note':'test','seeds':['https://official.example/data.csv']};writes=[];started=datetime.now(timezone.utc)
  def save(s,k,b,*a,**kw):
   writes.append(json.loads(b))
   return {'ETag':'"saved"'}
  with patch.dict('os.environ',{'CONSTELLATION_ROLE':'worker'}),patch('public_source_capture.read_json',return_value=(None,None)),patch('public_source_capture.put',side_effect=save),patch('public_source_capture.capture',side_effect=requests.exceptions.ChunkedEncodingError('connection dropped')):
   report=run(source,'historical',1,s3=Mock())
  delay=(datetime.fromisoformat(writes[0]['frontier'][0]['retry_after'])-started).total_seconds()
  self.assertTrue(800<delay<1000);self.assertEqual(report['failed_urls'],1);self.assertFalse(report['route_drained'])
 def test_transient_provider_503_retries_once_before_paid_fallback(self):
  from public_source_capture import capture
  body=b'one,two\n1,2\n';saved={};s3=Mock()
  s3.upload_file.side_effect=lambda path,bucket,key,ExtraArgs:saved.update({key:Path(path).read_bytes()})
  from botocore.response import StreamingBody
  s3.get_object.side_effect=lambda Bucket,Key:{'Body':StreamingBody(io.BytesIO(saved[Key]),len(saved[Key]))}
  busy=Mock(status_code=503,headers={});ok=Mock(status_code=200,headers={'Content-Type':'text/csv'});ok.__enter__=Mock(return_value=ok);ok.__exit__=Mock(return_value=False);ok.iter_content.return_value=iter([body])
  source={'source':'fixture','catalog_entry':999,'hosts':['official.example'],'scope_note':'test','http_transient_retries':1,'decodo':True}
  with patch('public_source_capture.requests.get',side_effect=[busy,ok])as get,patch('public_source_capture.time.sleep'),patch('public_source_capture.admit'),patch('public_source_capture.rendered')as fallback:
   record,_=capture(s3,source,{'url':'https://official.example/data.csv','depth':0},'daily',publish_receipt=False)
  self.assertEqual(get.call_count,2);fallback.assert_not_called();self.assertEqual(record['bytes'],len(body))
 def test_large_daily_source_cannot_download_on_controller(self):
  from public_source_capture import run
  with patch.dict('os.environ',{'CONSTELLATION_ROLE':'controller'}),patch('public_source_capture.capture')as capture:
   with self.assertRaisesRegex(ValueError,'requires_c7i'):run({'source':'brazil_anm_cfem_mining_royalties','daily_execution':'worker'},'daily',s3=Mock())
   capture.assert_not_called()
 def test_unrelated_spreadsheet_zip_is_not_ndb_workbook(self):
  import zipfile
  from metadata_engine.regional_public import validate_ndb_workbook
  with tempfile.TemporaryDirectory()as tmp:
   path=Path(tmp)/'fake.xlsx'
   with zipfile.ZipFile(path,'w')as archive:archive.writestr('document.xml','<other>'+('unrelated'*30)+'</other>')
   with self.assertRaisesRegex(RawFailure,'workbook_package_missing'):validate_ndb_workbook({'path':path,'bytes':path.stat().st_size})
 def test_staged_original_is_checked_but_not_sent_to_intake(self):
  from public_source_capture import capture
  from botocore.response import StreamingBody
  body=b'one,two\n1,2\n';saved={};s3=Mock()
  def upload(path,bucket,key,ExtraArgs):saved[key]=Path(path).read_bytes()
  s3.upload_file.side_effect=upload;s3.get_object.side_effect=lambda Bucket,Key:{'Body':StreamingBody(io.BytesIO(saved[Key]),len(saved[Key]))}
  response=Mock(status_code=200,headers={'Content-Type':'text/csv'});response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.iter_content.return_value=iter([body]);source={'source':'fixture','catalog_entry':999,'hosts':['official.example'],'scope_note':'test'}
  import builtins
  ordinary_import=builtins.__import__
  def unrelated_provider_absent(name,*args,**kwargs):
   if name=='open_medic_download':raise ModuleNotFoundError('Unrelated provider helper is not installed')
   return ordinary_import(name,*args,**kwargs)
  with patch('public_source_capture.requests.get',return_value=response),patch('public_source_capture.admit'),patch('public_source_capture.put')as put,patch('builtins.__import__',side_effect=unrelated_provider_absent):
   record,_=capture(s3,source,{'url':'https://official.example/data.csv','depth':0},'daily',publish_receipt=False)
  self.assertEqual(record['sha256'],hashlib.sha256(body).hexdigest());self.assertEqual(record['artifact_kind'],'public_document');put.assert_not_called()

class DailyWorkerQueue(unittest.TestCase):
 def test_yesterday_drained_crawl_does_not_permanently_stop_daily_dispatch(self):
  from constellation.legacy_dispatch import _dispatch
  from constellation.legacy_routes import route_hash
  from contextlib import contextmanager
  row={'unit':'constellation-public-daily-fixture.service','route_kind':'independent_public_daily','execution_enabled':True,'argv':['public_source_capture.py','--mode','daily'],'start_target':'2026-11-18','end_exclusive':'2026-11-19','cadence_seconds':21600}
  cursor=Mock();cursor.fetchone.side_effect=[{'result_json':json.dumps({'route_drained':True}),'spec_json':json.dumps({'end':row['end_exclusive'],'parameters':{'route_sha256':route_hash(row)}})},None]
  @contextmanager
  def db():yield cursor
  control=Mock();control.db=db;control.register.return_value='new-daily-job';control.allowed.return_value=True
  with patch('source_pauses.unit_pause',return_value=None),patch.dict('os.environ',{'CONSTELLATION_ROLE':'controller'}):result=_dispatch(control,row)
  self.assertEqual(result['status'],'queued_on_c7i');control.register.assert_called_once()

class NativePublicationFence(unittest.TestCase):
 def test_reviewed_source_does_not_publish_old_accepted_site_assets(self):
  from metadata_engine.controller import publish
  from contextlib import contextmanager
  cursor=Mock();cursor.fetchall.return_value=[]
  @contextmanager
  def tx():yield cursor
  db=Mock();db.tx=tx;db.cursor.return_value={};db.config={'contracts':{'brazil_anm_cfem_mining_royalties':{'contract_version':'2.0.3'}}}
  self.assertEqual(publish(db,source_key='brazil_anm_cfem_mining_royalties'),0)
  query,params=cursor.execute.call_args.args
  self.assertIn('AND contract_version=%s',query);self.assertEqual(params,('brazil_anm_cfem_mining_royalties','2.0.3'))

class DailyPauseFence(unittest.TestCase):
 def test_global_daily_pause_never_wakes_worker_for_large_files(self):
  from constellation import public_file_dispatch as dispatch
  with patch.object(dispatch,'Control')as control,patch.object(dispatch.m7_lifecycle,'dispatch')as wake,patch('sys.argv',['dispatch','--job','public-cfem-daily']):
   control.return_value.daily_allowed.return_value=False;self.assertEqual(dispatch.main(),0);wake.assert_not_called()
 def test_queued_large_daily_request_respects_pause_when_lifecycle_replays_it(self):
  from constellation import m7_lifecycle as lifecycle
  with patch('constellation.control.Control')as control,patch('constellation.m7_batch.acknowledged')as ack,patch('constellation.m7_batch.dispatch_allowed')as allowed,patch.object(lifecycle,'start')as start:
   control.return_value.daily_allowed.return_value=False;lifecycle.dispatch('optima-m7-capture-public-cfem-daily.service')
  ack.assert_called_once_with('optima-m7-capture-public-cfem-daily.service');allowed.assert_not_called();start.assert_not_called()

if __name__=='__main__':unittest.main()
