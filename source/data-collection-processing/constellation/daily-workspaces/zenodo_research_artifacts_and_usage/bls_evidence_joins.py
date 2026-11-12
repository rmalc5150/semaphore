"""Evidence joins for S59: release archives, quarterly compensation, RDS exposure."""
import copy
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo
from collection_storage import now, write_json
from disclosure_collection import get_bytes
from research_contract import ROOT,digest
from regulatory_collection import require,SourceIssue

VERSION='bls-evidence-joins-v2'
ARCHIVE='https://www.bls.gov/bls/news-release/empsit.htm'
COMP={
 'CIU2013000000000I':{'program':'ECI','measure':'total_compensation','unit':'index, December 2005=100'},
 'CIU2023000000000I':{'program':'ECI','measure':'wages_and_salaries','unit':'index, December 2005=100'},
 'CMU2013000000000D':{'program':'ECEC','measure':'total_compensation','unit':'USD/hour worked'},
 'CMU2023000000000D':{'program':'ECEC','measure':'wages_and_salaries','unit':'USD/hour worked'},
 'CMU2033000000000D':{'program':'ECEC','measure':'benefits','unit':'USD/hour worked'},
}


def cached(client,name,build,ttl=86400):
    """Persist data AND its evidence; failures have a short retry lifetime."""
    memory=getattr(client,'_bls_join_cache',{})
    if name in memory:
        result,evidence=memory[name];client.evidence.extend(copy.deepcopy(evidence));return copy.deepcopy(result)
    key='operations/bls-labor/joins-cache/'+name+'.json'
    existing=client.store.get(key)
    old=json.loads(existing.body) if existing else None
    if old and (datetime.now(timezone.utc)-datetime.fromisoformat(old['checked_at'].replace('Z','+00:00'))).total_seconds()<old['ttl']:
        memory[name]=(old['result'],old['evidence']);client._bls_join_cache=memory
        client.evidence.extend(old['evidence']);return copy.deepcopy(old['result'])
    start=len(client.evidence)
    result=build()
    snapshot={'checked_at':now(),'ttl':3600 if result.get('status')=='retry_pending' else ttl,
        'result':result,'evidence':copy.deepcopy(client.evidence[start:])}
    write_json(client.store,key,snapshot,existing.token if existing else None)
    memory[name]=(result,snapshot['evidence']);client._bls_join_cache=memory
    return result


class Links(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.href=None;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.href=dict(attrs).get('href');self.parts=[]
    def handle_data(self,data):
        if self.href:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.href:self.rows.append((self.href,' '.join(self.parts)));self.href=None


class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.tables=[];self.table=None;self.row=None;self.cell=None;self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.table={'text':[],'rows':[]}
        if tag=='tr' and self.table is not None:self.row=[]
        if tag in {'td','th'} and self.row is not None:self.cell=[]
    def handle_data(self,data):
        self.text.append(data)
        if self.table is not None:self.table['text'].append(data)
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in {'td','th'} and self.cell is not None:
            self.row.append(' '.join(self.cell).strip());self.cell=None
        if tag=='tr' and self.row is not None:
            self.table['rows'].append(self.row);self.row=None
        if tag=='table' and self.table is not None:self.tables.append(self.table);self.table=None


def archive_index(raw):
    parser=Links();parser.feed(raw.decode())
    months='January February March April May June July August September October November December'.split()
    result={}
    for href,label in parser.rows:
        m=re.search(r'('+'|'.join(months)+r') (20\d\d) Employment Situation',label)
        url=urljoin(ARCHIVE,href)
        if m and re.fullmatch(r'https://www\.bls\.gov/news\.release/archives/empsit_\d{8}\.htm',url):
            p=m[2]+'-'+f'{months.index(m[1])+1:02}'
            date=datetime.strptime(url[-12:-4],'%m%d%Y').date().isoformat()
            result[p]={'url':url,'first_release_date':date,'date_precision':'day',
                       'basis':'official archive month label and dated release permalink'}
    require(result,'bls_archive_index_unparsed');return result


def release_index(client):
    def build():
        try:
            raw=client.get(ARCHIVE)
            require(b'Access Denied' not in raw,'bls_archive_access_denied')
            return {'status':'checked','periods':archive_index(raw),'source_url':ARCHIVE}
        except (SourceIssue,ValueError) as exc:
            return {'status':'retry_pending','reason':getattr(exc,'code',type(exc).__name__),'periods':{}}
    result=cached(client,'release-index-v2',build)
    path=ROOT/'config/bls-release-bootstrap.json'
    if path.exists():
        bootstrap=json.loads(path.read_text())
        # Browser-retrieved official index extract is a separately labeled fallback.
        cache=getattr(client,'_bls_bootstrap_evidence',None)
        if cache:client.evidence.extend(copy.deepcopy(cache))
        else:
            start=len(client.evidence)
            client.save(json.dumps(bootstrap,sort_keys=True).encode(),ARCHIVE,'application/json')
            client._bls_bootstrap_evidence=copy.deepcopy(client.evidence[start:])
        periods={**bootstrap['periods'],**result['periods']}
        return {**result,'periods':periods,'bootstrap_retrieved_at':bootstrap['retrieved_at'],
                'not_published':bootstrap.get('not_published',{})}
    return result


def archived_values(client,entry,p):
    """Use full direct HTML when available; otherwise a pinned official web excerpt."""
    bootstrap=ROOT/'config/bls-release-vintages.json'
    if bootstrap.exists():
        data=json.loads(bootstrap.read_text()).get('periods',{}).get(p)
        if data:
            require(data['source_url']==entry['url'] and data['reference_period']==p and data['series']=='CES3000000003','bls_bootstrap_identity_mismatch')
            client.save(json.dumps(data,sort_keys=True).encode(),entry['url'],'application/json')
            return data
    def build():
        try:
            raw=client.get(entry['url']);require(b'Access Denied' not in raw,'bls_archive_access_denied')
            parser=Tables();parser.feed(raw.decode())
            text=' '.join(parser.text)
            header=re.search(r'(\d{1,2}:\d{2})\s*a\.m\.\s*\(ET\)\s*\w+,\s*(\w+ \d{1,2}, \d{4})',text)
            stamp=None
            if header:
                stamp=datetime.strptime(header[2]+' '+header[1],'%B %d, %Y %H:%M').replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat().replace('+00:00','Z')
            for table in parser.tables:
                label=' '.join(table['text'])
                if not ('Average hourly' in label and 'all employees' in label and 'seasonally adjusted' in label and 'not seasonally adjusted' not in label):continue
                for cells in table['rows']:
                    if cells and cells[0].strip()=='Manufacturing' and len(cells)==9:
                        month=datetime.strptime(p,'%Y-%m').strftime('%b')
                        require(month in label and p[:4] in label,'bls_release_period_header_missing')
                        return {'status':'recovered','reference_period':p,'series':'CES3000000003',
                            'value':cells[4].replace('$','').replace(',',''),'official_published_at':stamp,
                            'table':'B-3','extraction_basis':'manufacturing current-month AHE column of eight-value B-3 row',
                            'source_url':entry['url'],'retrieved_at':now()}
            return {'status':'retry_pending','reason':'bls_release_table_unparsed'}
        except (SourceIssue,ValueError,ImportError) as exc:
            return {'status':'retry_pending','reason':getattr(exc,'code',type(exc).__name__)}
    return cached(client,'release-'+p,build)


def publication_join(client,row):
    from bls_enrichment import period,number
    p=period(row)
    if p.endswith('annual'):return {'status':'not_applicable_annual_average','point_in_time_eligible':False}
    index=release_index(client)
    entry=index['periods'].get(p)
    if not entry:
        if p in index.get('not_published',{}):
            return {'status':'documented_no_separate_release','reference_period':p,'reason':index['not_published'][p],
                'source_url':ARCHIVE,'point_in_time_eligible':False}
        return {'status':'retry_pending','reason':'release_index_missing_reference_month','reference_period':p,'point_in_time_eligible':False}
    vintage=archived_values(client,entry,p)
    return {'status':'joined' if vintage.get('status')=='recovered' else 'retry_pending',
        'reference_period':p,'first_release':entry,'original_release_vintage':vintage,
        'saved_value_matches_original':number(row['value'])==number(vintage.get('value')) if vintage.get('status')=='recovered' else None,
        'current_saved_value_published_at':None,'point_in_time_eligible':False,
        'temporal_note':'First-release date belongs to the separately archived release value. A later API value never inherits it, even if numerically equal.'}


def compensation_history(client,year):
    # Seven retained years fit one public API request; share across daily pages/backfill.
    panel_end=datetime.now(timezone.utc).year
    panel_start=max(2020,panel_end-9)
    if year<panel_start:panel_start,panel_end=year-1,year
    def build():
        from bls_enrichment import API
        try:
            data=client.json(API,body={'seriesid':list(COMP),'startyear':str(panel_start),'endyear':str(panel_end)})
            require(data.get('status')=='REQUEST_SUCCEEDED','bls_compensation_provider_error')
            rows=data.get('Results',{}).get('series',[])
            require({s['seriesID'] for s in rows}==set(COMP),'bls_compensation_series_missing')
            require(all(s['data'] for s in rows),'bls_compensation_empty')
            return {'status':'checked','series':{s['seriesID']:s['data'] for s in rows},'retrieved_at':now()}
        except SourceIssue as exc:return {'status':'retry_pending','reason':exc.code}
    return cached(client,'compensation-panel-'+str(panel_start)+'-'+str(panel_end),build)


def compensation_join(client,row):
    from bls_enrichment import number
    data=compensation_history(client,int(row['year']))
    if data['status']!='checked':return data
    if row['period']=='M13':return {'status':'not_applicable_annual_average','point_in_time_eligible':False}
    quarter='Q'+f'{(int(row["period"][1:])-1)//3+1:02}'
    observations=[]
    for series,rows in data['series'].items():
        match=next((r for r in rows if r['year']==row['year'] and r['period']==quarter),None)
        if match:observations.append({'series':series,**COMP[series],'observation':match})
    matched={r['measure']:r for r in observations if r['program']=='ECEC'}
    arithmetic=None
    if set(matched)=={'total_compensation','wages_and_salaries','benefits'}:
        total,wage,benefit=[number(matched[k]['observation']['value']) for k in ['total_compensation','wages_and_salaries','benefits']]
        if all(x is not None for x in (total,wage,benefit)):
            arithmetic={'total_minus_wages_minus_benefits':str(total-wage-benefit),'rounding_tolerance':'0.02',
                'reconciled':abs(total-wage-benefit)<=Decimal('0.02'),
                'manufacturing_benefits_share_percent':str(benefit/total*100) if total else None}
    latest=max((int(r['year']),r['period']) for rows in data['series'].values() for r in rows)
    status='joined' if len(observations)==len(COMP) else ('quarter_not_yet_available' if (int(row['year']),quarter)>latest else 'retry_pending')
    if status=='joined' and (arithmetic is None or not arithmetic['reconciled']):status='retry_pending'
    return {'status':status,
        'reference_year':row['year'],'reference_quarter':quarter,'frequency':'quarterly',
        'geography':'United States','industry':'manufacturing, NAICS 31-33','population':'private industry workers',
        'seasonally_adjusted':False,'observations':observations,'reconciliation':arithmetic,
        'retrieved_at':data['retrieved_at'],'official_published_at':None,'point_in_time_eligible':False,
        'join_basis':'same reference quarter, descriptive current-vintage context; never a monthly interpolation or historical as-of join',
        'comparability_note':'CES uses hours paid; ECEC costs use hours worked. Do not multiply CES by an ECEC ratio to assert a company cost.',
        'company_fully_loaded_cost':None}


def assess_exposure(directory):
    """Admit only reviewed manufacturer relationships with explicit US territory and evidence."""
    companies={c['company_id']:c for c in directory.get('companies',[]) if c.get('review_status')=='verified' and not c.get('archived_at')}
    products={p['product_id']:p for p in directory.get('products',[]) if p.get('review_status')=='verified' and not p.get('archived_at')}
    links=[];candidates=[]
    for rel in directory.get('relationships',[]):
        if rel.get('company_id') not in companies or rel.get('product_id') not in products:continue
        record={'company_id':rel['company_id'],'product_id':rel['product_id'],'relationship_id':rel['relationship_id'],
            'role':rel.get('role'),'territory':rel.get('territory'),'evidence':rel.get('evidence'),
            'valid_from':rel.get('valid_from'),'valid_to':rel.get('valid_to'),'observed_at':rel.get('observed_at')}
        # Territory on a commercial relationship need not describe a factory. Require structured manufacturing-site evidence too.
        attributes=products[rel['product_id']].get('attributes') or {}
        if isinstance(attributes,str):attributes=json.loads(attributes)
        sites=attributes.get('manufacturing_locations',[])
        verified_sites=[s for s in sites if isinstance(s,dict) and s.get('country_code')=='US' and s.get('operator_company_id')==rel['company_id'] and s.get('review_status')=='verified' and s.get('evidence')]
        today=datetime.now(timezone.utc).date().isoformat()
        current=(not rel.get('valid_from') or str(rel['valid_from'])<=today) and (not rel.get('valid_to') or str(rel['valid_to'])>today)
        if current and rel.get('role')=='manufacturer' and rel.get('review_status')=='verified' and rel.get('evidence') and verified_sites:
            links.append({**record,'manufacturing_sites':verified_sites,'applicability':'broad US manufacturing labor context',
                'confidence':'evidenced_activity; cost magnitude unknown','company_labor_share':None,
                'historical_exposure_eligible':False,'product_sector':products[rel['product_id']].get('sector_id')})
        else:candidates.append({**record,'reason':'requires verified manufacturer role and evidenced US manufacturing site'})
    return {'status':'checked','company_count':len(companies),'product_count':len(products),'relationship_count':len(directory.get('relationships',[])),
        'company_links':links,'review_candidates':candidates,'unmatched_company_ids':sorted(set(companies)-{r['company_id'] for r in links}),
        'snapshot_basis':'current read-only RDS evidence; domicile and sector do not prove factory location',
        'point_in_time_eligible':False,'admission':'no RDS writes or new entities'}


def exposure_join(client):
    return {'status':'retired_registry','reason':'company_exposure_join_retired_by_owner'}


def add_joins(client,row,enrichment):
    joins={'publication':publication_join(client,row),'compensation':compensation_join(client,row),'company_exposure':exposure_join(client)}
    enrichment['evidence_joins']={'version':VERSION,**joins}
    enrichment['compensation_context']=joins['compensation']
    enrichment['sector_exposure']=joins['company_exposure']
    enrichment['timing']['publication_evidence_status']=joins['publication']['status']
    enrichment['join_status']='retry_pending' if any(j['status']=='retry_pending' for j in joins.values()) else 'assessed'
    enrichment['status']='enriched_with_pending_evidence' if enrichment['join_status']=='retry_pending' else 'enriched'
    return enrichment
