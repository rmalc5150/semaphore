"""S57 archive provenance, interval prices and conservative storage indicators."""
import csv
import hashlib
import io
import json
import math
import re
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from research_contract import digest

VERSION='caiso-market-evidence-v1'
PACIFIC=ZoneInfo('America/Los_Angeles')
UTC=timezone.utc
COMPONENTS={'LMP':'total','MCE':'energy','MCC':'congestion','MCL':'loss','MGHG':'ghg'}
HUB_NODES={'TH_NP15_GEN-APND','TH_SP15_GEN-APND','TH_ZP26_GEN-APND'}
REPORTS=[{'queryname':'PRC_LMP','version':12,'market_run_id':'DAM','minutes':60},
         {'queryname':'PRC_INTVL_LMP','version':3,'market_run_id':'RTM','minutes':5},
         {'queryname':'PRC_RTPD_LMP','version':3,'market_run_id':'RTPD','minutes':15},
         {'queryname':'PRC_AS','version':12,'market_run_id':'DAM','minutes':60},
         {'queryname':'PRC_INTVL_AS','version':1,'market_run_id':'RTM','minutes':15}]


def instant(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None:raise ValueError('CAISO interval requires explicit timezone')
    return parsed.astimezone(UTC)


def number(value):
    try:
        result=Decimal(str(value))
        return result if result.is_finite() else None
    except InvalidOperation:return None


def timing(row):
    start,end=instant(row['INTERVALSTARTTIME_GMT']),instant(row['INTERVALENDTIME_GMT'])
    if end<=start:raise ValueError('Invalid CAISO interval bounds')
    local=start.astimezone(PACIFIC)
    return {'start_utc':start.isoformat().replace('+00:00','Z'),'end_utc':end.isoformat().replace('+00:00','Z'),
            'start_pacific':local.isoformat(),'end_pacific':end.astimezone(PACIFIC).isoformat(),
            'pacific_fold':local.fold,'operating_date_reported':row.get('OPR_DT'),
            'operating_date_calculated':local.date().isoformat(),'operating_hour_reported':row.get('OPR_HR'),
            'operating_interval_reported':row.get('OPR_INTERVAL'),
            'duration_minutes':(end-start).total_seconds()/60,
            'operating_date_matches':not row.get('OPR_DT') or row['OPR_DT']==local.date().isoformat()}


def parse_archive(raw,query,archive_evidence=None,nodes=None,max_expanded=128*1024*1024):
    if not raw.startswith(b'PK'):raise ValueError('CAISO response is not a ZIP')
    archive_sha=hashlib.sha256(raw).hexdigest();records=[];members=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos=z.infolist()
        if len(infos)>1000 or sum(i.file_size for i in infos)>max_expanded:raise ValueError('CAISO ZIP expansion cap')
        if len({i.filename for i in infos})!=len(infos):raise ValueError('Duplicate CAISO ZIP member name')
        for info in infos:
            if info.is_dir():continue
            if info.filename.startswith('/') or '..' in info.filename.split('/'):raise ValueError('Unsafe archive member')
            if not info.filename.lower().endswith('.csv'):
                # Error XML is evidence, not a successfully empty market window.
                from lxml import etree
                if info.filename.lower().endswith('.xml'):
                    content=z.read(info)
                    root=etree.fromstring(content,etree.XMLParser(resolve_entities=False,no_network=True))
                    error=root.xpath('//*[local-name()="ERR_CODE" or local-name()="ERR_DESC"]/text()')
                    if error:raise ValueError('CAISO report error: '+'; '.join(error))
                raise ValueError('Unsupported CAISO member: '+info.filename)
            class Hasher(io.RawIOBase):
                def __init__(self,source):self.source=source;self.sha=hashlib.sha256();self.count=0
                def readable(self):return True
                def readinto(self,b):
                    value=self.source.read(len(b));b[:len(value)]=value;self.sha.update(value);self.count+=len(value);return len(value)
            stream=Hasher(z.open(info))
            text=io.TextIOWrapper(io.BufferedReader(stream),encoding='utf-8-sig',newline='')
            reader=csv.DictReader(text)
            count=selected=0
            first_selected=len(records)
            for count,row in enumerate(reader,1):
                if not row.get('INTERVALSTARTTIME_GMT') or not row.get('INTERVALENDTIME_GMT'):raise ValueError('CAISO row lacks interval bounds')
                node=row.get('NODE') or row.get('NODE_ID') or row.get('PNODE_RESMRID')
                if nodes and node not in nodes:continue
                selected+=1
                value_key=next((k for k in ('VALUE','MW','PRC') if k in row),None)
                if value_key is None:raise ValueError('CAISO price value column missing')
                price=number(row[value_key])
                provenance={'archive_sha256':archive_sha,'member_name':info.filename,'member_sha256':None,
                    'member_row':count,'query':query,'report_version':query.get('version'),
                    'archive_evidence':archive_evidence,'original_value_field':value_key}
                records.append({'raw':row,'price':str(price) if price is not None else None,
                    'timing':timing(row),'provenance':provenance,'node':node,
                    'market':row.get('MARKET_RUN_ID') or query.get('market_run_id'),
                    'component':row.get('LMP_TYPE'),'quality_gaps':[] if price is not None else ['non_numeric_price']})
            sha=stream.sha.hexdigest()
            for row in records[first_selected:]:row['provenance']['member_sha256']=sha
            members.append({'filename':info.filename,'sha256':sha,'bytes':stream.count,'crc32':f'{info.CRC:08x}',
                            'row_count':count,'selected_row_count':selected,'columns':reader.fieldnames})
            text.close()
    if not members:raise ValueError('Empty CAISO ZIP')
    return {'version':VERSION,'archive_sha256':archive_sha,'archive_bytes':len(raw),'members':members,
            'query':query,'archive_evidence':archive_evidence,'rows':records,
            'selected_row_count':len(records),'total_row_count':sum(m['row_count'] for m in members)}


def interval_prices(archive):
    groups=defaultdict(list)
    for row in archive['rows']:
        if row['component'] in COMPONENTS:
            groups[(row['node'],row['market'],row['timing']['start_utc'],row['timing']['end_utc'])].append(row)
    out=[]
    for identity,rows in sorted(groups.items()):
        node,market,start,end=identity;components=defaultdict(list)
        for r in rows:components[r['component']].append(r)
        gaps=[]
        if any(len(rs)!=1 for rs in components.values()):gaps.append('duplicate_component_rows')
        values={name:(rs[0]['price'] if len(rs)==1 else None) for name,rs in components.items()}
        legacy=(market=='DAM' and node in HUB_NODES and rows[0]['timing']['operating_date_calculated']<'2026-05-01'
                and set(components)=={'LMP','MCE','MCC','MCL'})
        required=('LMP','MCE','MCC','MCL') if legacy else tuple(COMPONENTS)
        missing=[name for name in required if values.get(name) is None]
        if missing:gaps.append('missing_or_non_numeric_components:'+','.join(missing))
        residual=None
        if not gaps:
            residual=Decimal(values['LMP'])-sum(Decimal(values[k]) for k in required if k!='LMP')
            if abs(residual)>Decimal('0.001'):gaps.append('component_reconciliation_failed')
        times=rows[0]['timing']
        if not all(r['timing']['operating_date_matches'] for r in rows):gaps.append('operating_date_mismatch')
        out.append({'interval_id':digest([node,market,start,end]),'node':node,'market':market,
            'timing':times,'prices_usd_per_mwh':{COMPONENTS[k]:values.get(k) for k in COMPONENTS},
            'component_definition':{'formula':'LMP = MCE + MCC + MCL' if legacy else 'LMP = MCE + MCC + MCL + MGHG','tolerance_usd_per_mwh':'0.001',
                'profile_id':'legacy_caiso_dam_hubs_three_components_v1' if legacy else 'four_reported_components_v1',
                'source':'https://www.caiso.com/documents/oasis-interfacespecification_v5_1_2clean_fall2017release.pdf' if legacy else 'https://www.caiso.com/documents/business-practice-manual-market-instruments-dame.pdf',
                'source_pdf_pages':[18,72] if legacy else [134],
                'missing_ghg_policy':'legacy_DAM_profile_does_not_publish_GHG; value_remains_null' if legacy else 'not_assumed_zero; unknown_schema_requires_review'},
            'reconciliation_residual':str(residual) if residual is not None else None,
            'reconciliation_status':'validated' if not gaps else 'review_required','quality_gaps':gaps,
            'raw_component_rows':[{k:r[k] for k in ['component','price','provenance','quality_gaps']} for r in rows],
            'revision_id':digest([identity,values]),'archive_version_id':archive['archive_sha256'],
            'event_status':'interval_observation_not_company_event'})
    return out


def collect_rows(client,job,item):
    from collection_storage import write_checked
    from regulatory_collection import SourceIssue
    query=job['parameters']['query'];url=job['parameters']['url']
    raw=client.get(url,params=query)
    evidence=next((e for e in reversed(client.evidence) if e['sha256']==hashlib.sha256(raw).hexdigest()),None)
    try:
        archive=parse_archive(raw,query,evidence,nodes={query['node']} if query.get('node') else None)
    except ValueError as exc:
        raise SourceIssue('caiso_no_data_returned' if str(exc).startswith('CAISO report error: 1000;') else 'caiso_error_or_non_csv_member',
                          diagnostics={'parser_message': str(exc)[:500]}) from None
    summary={k:v for k,v in archive.items() if k!='rows'}
    body=json.dumps(summary,sort_keys=True).encode();sha=hashlib.sha256(body).hexdigest()
    path='source_documents/caiso_archive_inventory/'+sha
    write_checked(client.store,path,body,content_type='application/json')
    rows=[]
    for record in archive['rows']:
        original=record['raw']
        data={'unit':'USD/MW (ancillary clearing price as published; settlement basis not inferred)' if original.get('ANC_TYPE') else 'USD/MWh',
              **original,'enrichment':{'version':VERSION,'timing':record['timing'],
                'provenance':record['provenance'],'price':record['price'],
                'archive_inventory_reference':{'key':path,'sha256':sha}}}
        identity=digest({k:v for k,v in original.items() if k not in {'VALUE','MW','PRC'}})
        rows.append(item(identity,data,url,record['timing']['start_utc'],'derived'))
    if not rows:raise SourceIssue('caiso_empty_selected_interval')
    return rows,None


def indicators(intervals,spike='200',congestion='50'):
    groups=defaultdict(list)
    for row in intervals:groups[(row['node'],row['market'],row['timing']['operating_date_calculated'])].append(row)
    out=[]
    for (node,market,day),rows in sorted(groups.items()):
        rows.sort(key=lambda r:r['timing']['start_utc'])
        start=datetime.fromisoformat(day).replace(tzinfo=PACIFIC)
        hours=(start+timedelta(days=1)).astimezone(UTC)-start.astimezone(UTC)
        expected_minutes=hours.total_seconds()/60
        unique={r['timing']['start_utc']:r for r in rows}
        covered=sum(r['timing']['duration_minutes'] for r in unique.values())
        contiguous=all(a['timing']['end_utc']==b['timing']['start_utc'] for a,b in zip(rows,rows[1:]))
        full=bool(rows) and len(unique)==len(rows) and contiguous and covered==expected_minutes and instant(rows[0]['timing']['start_utc'])==start.astimezone(UTC)
        valid=[r for r in rows if r['prices_usd_per_mwh']['total'] is not None]
        prices=[Decimal(r['prices_usd_per_mwh']['total']) for r in valid]
        negative=sum(r['timing']['duration_minutes']/60 for r in valid if Decimal(r['prices_usd_per_mwh']['total'])<0)
        episodes=[];active=None
        for row in rows:
            value=row['prices_usd_per_mwh']['congestion']
            hit=value is not None and abs(Decimal(value))>=Decimal(congestion)
            if hit:
                if active and active['end_utc']==row['timing']['start_utc']:
                    active['end_utc']=row['timing']['end_utc'];active['minutes']+=row['timing']['duration_minutes']
                else:
                    active={'start_utc':row['timing']['start_utc'],'end_utc':row['timing']['end_utc'],'minutes':row['timing']['duration_minutes']};episodes.append(active)
            else:active=None
        # Time-respecting single-interval charge/discharge spread; no hindsight revenue claim.
        best=None;minimum=None;best_pair=None
        for row,price in zip(valid,prices):
            if minimum is not None and (best is None or price-minimum[0]>best):
                best=price-minimum[0];best_pair={'charge_start_utc':minimum[1],'discharge_start_utc':row['timing']['start_utc']}
            if minimum is None or price<minimum[0]:minimum=(price,row['timing']['start_utc'])
        weighted=None
        if prices:
            total_minutes=sum(r['timing']['duration_minutes'] for r in valid)
            mean=sum(float(p)*r['timing']['duration_minutes'] for p,r in zip(prices,valid))/total_minutes
            weighted=math.sqrt(sum((float(p)-mean)**2*r['timing']['duration_minutes'] for p,r in zip(prices,valid))/total_minutes)
        out.append({'node':node,'market':market,'operating_date':day,'scope':'complete_pacific_operating_day' if full and len(valid)==len(rows) else 'partial_operating_day',
            'interval_count':len(rows),'expected_minutes':expected_minutes,'observed_minutes':covered,
            'negative_total_price_hours':negative,'price_spike_threshold_usd_per_mwh':spike,
            'price_spike_intervals':sum(p>=Decimal(spike) for p in prices),
            'absolute_congestion_threshold_usd_per_mwh':congestion,'congestion_episodes':episodes,
            'duration_weighted_price_stddev_usd_per_mwh':weighted,
            'min_total_price':str(min(prices)) if prices else None,'max_total_price':str(max(prices)) if prices else None,
            'chronological_single_interval_spread_usd_per_mwh':str(max(best,Decimal(0))) if best is not None else None,
            'spread_pair':best_pair,'spread_assumptions':'Observed-price diagnostic only; no efficiency, degradation, dispatch, capacity, duration, fees or availability constraints; not storage revenue',
            'storage_revenue_estimate':None,'revenue_estimate_status':'requires_documented_asset_efficiency_duration_degradation_and_operating_constraints',
            'source_interval_revision_ids':[r['revision_id'] for r in rows],
            'quality_gap_count':sum(bool(r['quality_gaps']) for r in rows)})
    return out


def project_exposures(intervals,mappings,directory):
    companies={r['company_id']:r for r in directory.get('companies',[]) if r['review_status']=='verified' and not r.get('archived_at')}
    products={r['product_id']:r for r in directory.get('products',[]) if r['review_status']=='verified' and not r.get('archived_at')}
    results=[]
    for mapping in mappings:
        if mapping.get('review_status')!='verified' or not mapping.get('evidence') or mapping.get('node_type')!='project_node':continue
        if mapping.get('node') in HUB_NODES:continue
        for row in intervals:
            day=row['timing']['operating_date_calculated']
            if row['node']!=mapping['node'] or (mapping.get('valid_from') and day<mapping['valid_from']) or (mapping.get('valid_to') and day>=mapping['valid_to']):continue
            associations=[]
            for link in mapping.get('relationships',[]):
                if link.get('review_status')!='verified' or not link.get('evidence'):continue
                if link.get('valid_from') and day<link['valid_from']:continue
                if link.get('valid_to') and day>=link['valid_to']:continue
                if link.get('company_id') and link['company_id'] not in companies:continue
                if link.get('product_id') and link['product_id'] not in products:continue
                if link.get('role') not in {'owner','operator','installed_product'}:continue
                associations.append(link)
            results.append({'project_id':mapping['project_id'],'node':row['node'],'interval_id':row['interval_id'],
                'node_mapping':mapping,'verified_relationships':associations,'status':'documented_project_price_context',
                'financial_impact':'not_determined','product_performance':'not_inferred'})
    return results
