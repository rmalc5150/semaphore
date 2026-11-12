"""NIST evidence parsing and conservative product-mention/event rules."""
import csv
import hashlib
import io
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import re
from urllib.parse import urljoin,urlsplit,urlunsplit
from lxml import html
from research_contract import digest

VERSION='nist-robotics-evidence-v2'
HOSTS={'www.nist.gov','nist.gov','nvlpubs.nist.gov','data.nist.gov'}
ROOT_URL='https://www.nist.gov/el/robotics'


def canonical(url,base=ROOT_URL):
    p=urlsplit(urljoin(base,url))
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in {None,443}:return None
    return urlunsplit(('https',p.netloc,p.path,p.query,''))


def relevant_link(url,label):
    if not canonical(url):return False
    if re.search(r'\.(tar|gz|mp4|jpg|png|xlsx)$',url,re.I):return False
    if any(x in url for x in ['/people/','/news-events/','/careers','/about-nist','/search','/privacy']):return False
    if re.search(r'\.(csv|json|zip)$',url,re.I):return True
    return bool(re.search(r'robot|grasp|manipulat|percept|mobility|benchmark|test.method|dataset|peg.in.hole|calibrat|agility|nistpubs|\.pdf',url+' '+label,re.I))


def parse_document(raw,url):
    if raw.startswith(b'PK\x03\x04'):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            files=[{'name':i.filename,'bytes':i.file_size} for i in archive.infolist()]
        return {'title':urlsplit(url).path.rsplit('/',1)[-1],'text':json.dumps(files),'sections':[],'tables':[],'links':[],'kind':'archive','source_date':None,'archive_members':files,'extraction_status':'original_archive_saved_member_index_only','semantic_hash':hashlib.sha256(raw).hexdigest()}
    if raw.lstrip().startswith((b'{',b'[')) or urlsplit(url).path.lower().endswith(('.csv','.json')):
        value=raw.decode('utf-8-sig')
        links=[]
        if raw.lstrip().startswith((b'{',b'[')) or urlsplit(url).path.lower().endswith('.json'):
            parsed=json.loads(value);samples=parsed[:100] if isinstance(parsed,list) else parsed
            rows=len(parsed) if isinstance(parsed,list) else None
            def walk(value):
                if isinstance(value,dict):
                    for k,v in value.items():
                        if k.lower() in {'downloadurl','accessurl','contenturl'} and isinstance(v,str) and canonical(v):links.append({'url':canonical(v),'label':k})
                        elif isinstance(v,(list,dict)):walk(v)
                elif isinstance(value,list):
                    for v in value:walk(v)
            walk(parsed)
        else:
            reader=csv.DictReader(io.StringIO(value));samples=[];rows=0
            for row in reader:
                rows+=1
                if len(samples)<100:samples.append(row)
        return {'title':urlsplit(url).path.rsplit('/',1)[-1],'text':json.dumps(samples,ensure_ascii=False),
          'sections':[],'tables':[],'links':links,'kind':'dataset','source_date':None,
          'row_count':rows,'sample_rows':samples,'extraction_status':'source_data_archived_sample_index',
          'semantic_hash':digest(value)}
    if raw.startswith(b'%PDF-'):
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(raw));pages=[p.extract_text() or '' for p in reader.pages]
        text='\n\n'.join(pages)
        return {'title':str(reader.metadata.title or urlsplit(url).path.rsplit('/',1)[-1]) if reader.metadata else url,
                'text':text,'sections':[{'page':i+1,'text':v} for i,v in enumerate(pages)],'tables':[],
                'links':[],'kind':'pdf','source_date':None,'extraction_status':'text_extracted' if len(text.strip())>100 else 'ocr_needed',
                'semantic_hash':digest(re.sub(r'\s+',' ',text).strip())}
    if b'<html' not in raw.lower()[:8192] and b'<!doctype html' not in raw.lower()[:8192]:raise ValueError('Not HTML or PDF')
    doc=html.fromstring(raw)
    date_value=next(iter(doc.xpath('//meta[@name="citation_publication_date"]/@content | //meta[@property="article:published_time"]/@content')),None)
    date_fact={'source_value':date_value,'value':date_value[:10],'precision':'day'} if date_value and re.match(r'^\d{4}-\d{2}-\d{2}',date_value) else None
    main=next(iter(doc.xpath('//main')),None)
    if main is None:main=next(iter(doc.xpath('//*[@id="main-content" and (child::* or normalize-space(text())!="")]')),doc)
    for element in main.xpath('.//script | .//style | .//nav | .//header | .//footer | .//*[contains(@class,"breadcrumb")]'):
        element.drop_tree()
    title=' '.join(main.xpath('.//h1//text()')).strip() or ' '.join(doc.xpath('//title/text()')).strip()
    links=[]
    for a in main.xpath('.//a[@href]'):
        label=' '.join(a.text_content().split());target=canonical(a.get('href'),url)
        if target and relevant_link(target,label):links.append({'url':target,'label':label})
    tables=[[[ ' '.join(c.text_content().split()) for c in row.xpath('./th|./td')] for row in table.xpath('.//tr')] for table in main.xpath('.//table')]
    sections=[{'heading':e.tag,'text':' '.join(e.text_content().split())} for e in main.xpath('.//h1|.//h2|.//h3|.//p|.//li')]
    text=' '.join(main.text_content().split())
    if not text.strip():raise ValueError('NIST main document text missing')
    # Last-updated boilerplate is provenance, not substantive document change.
    text=re.sub(r'(?:Created|Updated)\s+\w+\s+\d{1,2},\s+\d{4}','',text)
    return {'title':title,'text':text,'sections':sections,'tables':tables,'links':list({r['url']:r for r in links}.values()),
            'kind':'discovery' if url.rstrip('/')==ROOT_URL else 'publication' if '/publications/' in url else 'method' if re.search(r'test method|benchmark|protocol|dataset',title,re.I) else 'project',
            'source_date':date_fact,'extraction_status':'text_extracted','semantic_hash':digest([title,text])}


def product_mentions(document,directory):
    text=document['text'];matches=[]
    active={r['product_id']:r for r in directory['products'] if not r['archived_at'] and r['review_status']=='verified' and r['sector_id']=='robotics'}
    names=[(pid,p['canonical_name'],'canonical') for pid,p in active.items()]
    reference_day=(document.get('source_date') or {}).get('value') or datetime.now(ZoneInfo('Europe/Madrid')).date().isoformat()
    names += [(r['product_id'],r['alias'],'alias') for r in directory['aliases'] if r['product_id'] in active and r['review_status']=='verified' and (not r.get('valid_from') or r['valid_from']<=reference_day) and (not r.get('valid_to') or r['valid_to']>reference_day)]
    for pid,name,basis in names:
        if len(name.strip())<3:continue
        # Numeric model names or multiple words are more specific than Spot/Stretch/etc.
        specific=bool(re.search(r'\d',name)) or len(name.split())>1
        for m in re.finditer(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text,re.I):
            context=text[max(0,m.start()-220):m.end()+220]
            manufacturers=[r['canonical_name'] for r in directory['companies'] if r['product_id']==pid and r['review_status']=='verified']
            corroborated=specific or any(re.search(re.escape(n),context,re.I) for n in manufacturers)
            matches.append({'product_id':pid,'matched_name':name,'basis':basis,
                 'match_status':'exact_registry_mention' if corroborated else 'ambiguous_name_review',
                 'relation':'mentioned_not_proven_tested','character_span':[m.start(),m.end()],'supporting_text':context})
            break
    return matches


def evidence_event(document,url,matches):
    linked=sorted({r['product_id'] for r in matches if r['match_status']=='exact_registry_mention'})
    if not linked or document['kind'] in {'discovery','project'} or document['extraction_status']!='text_extracted':return None
    identity=digest([url,document['semantic_hash']])
    return {'event_id':'nist_evt_'+identity,'event_type':'robotics_research_evidence_observed',
      'status':'candidate','review_status':'pending','product_ids':linked,
      'summary':document['title'],'occurrence':document['source_date'],
      'date_basis':'explicit_source_publication_date' if document['source_date'] else 'publication_date_unknown',
      'relation':'product_mentioned; benchmark performance and tested configuration require review',
      'point_in_time_eligible':False,'model_outputs':None}
