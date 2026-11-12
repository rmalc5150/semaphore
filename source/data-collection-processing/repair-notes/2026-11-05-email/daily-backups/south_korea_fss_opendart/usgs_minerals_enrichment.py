"""Full-report USGS MCS extraction with geometry, vintage and exposure provenance."""
import copy
import hashlib
import io
import json
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pathlib import Path

import pdfplumber
from collection_storage import now, write_json
from research_contract import ROOT, digest
from regulatory_collection import require, SourceIssue

VERSION='usgs-minerals-evidence-v2'
HEADINGS=['Domestic Production and Use','Salient Statistics','Recycling','Import Sources','Tariff',
 'Depletion Allowance','Government Stockpile','Events, Trends, and Issues','World Mine Production and Reserves',
 'World Production and Reserves','World Resources','Substitutes']


def document_identity(url):
    m=re.fullmatch(r'https://pubs\.usgs\.gov/periodicals/mcs(\d{4})/mcs\1-(lithium|cobalt|nickel|graphite)\.pdf',url)
    require(m is not None,'usgs_untrusted_report_url')
    return int(m[1]),m[2]


def lines(page):
    words=page.extract_words(extra_attrs=['size'])
    result=[]
    for w in sorted(words,key=lambda w:(w['top'],w['x0'])):
        row=next((r for r in reversed(result[-3:]) if abs(r['top']-w['top'])<2.5),None)
        if row is None: row={'top':w['top'],'words':[]};result.append(row)
        row['words'].append(w)
    for row in result:
        row['words'].sort(key=lambda w:w['x0'])
        row['text']=' '.join(w['text'] for w in row['words'])
        row['bbox']=[min(w['x0'] for w in row['words']),min(w['top'] for w in row['words']),
                     max(w['x1'] for w in row['words']),max(w['bottom'] for w in row['words'])]
    return sorted(result,key=lambda r:r['top'])


def split_words(words, normal_size):
    main=[w['text'] for w in words if w['size']>=normal_size*.8]
    markers=[w['text'] for w in words if w['size']<normal_size*.8]
    return ' '.join(main).strip(),markers


def value_cell(words, normal_size, dash_definition):
    text,markers=split_words(words,normal_size)
    raw=' '.join(w['text'] for w in words)
    cleaned=text.replace(',','').strip()
    flags=[];status='numeric';value=None
    if cleaned in {'NA','N/A','Not available'}:status='not_available'
    elif cleaned=='W':status='withheld'
    elif re.fullmatch(r'\(\s*\d*\s*\)',cleaned):status='footnote_reference'
    elif cleaned in {'—','--','–','-'}:
        status='defined_zero' if dash_definition=='zero' else 'dash_unresolved'
        value='0' if status=='defined_zero' else None
    else:
        match=re.fullmatch(r'([<>~]?)([-+]?\d+(?:\.\d+)?)([er]?)',cleaned)
        if match:
            value=match[2]
            if match[1]:flags.append({'qualifier':match[1]});status='qualified_numeric'
            if match[3]:markers.append(match[3])
        else:status='unparsed'
    return {'raw_cell':raw,'value':value,'status':status,'markers':markers,'qualifiers':flags}


def unit_for(label,group,default):
    text=(group+' '+label).lower()
    if 'percentage' in text or 'percent' in text:return {'unit':'percent','scale':'1','material_basis':None}
    if 'dollar' in text or 'price' in text:
        if 'pound' in text:return {'unit':'USD/lb','scale':'1','material_basis':None}
        if 'kilogram' in text:return {'unit':'USD/kg','scale':'1','material_basis':None}
        if 'metric ton' in text:return {'unit':'USD/metric_ton','scale':'1','material_basis':None}
        return {'unit':None,'scale':None,'material_basis':None,'unit_review':'price_unit_not_resolved'}
    return dict(default)


def stats_table(rows, page_number, caption, edition, dash):
    out=[];gaps=[]
    header=next((r for r in rows if 'Salient Statistics' in r['text']),None)
    if not header:return out,gaps
    yearwords=[w for w in header['words'] if re.fullmatch(r'20\d{2}',w['text'])]
    if not 3<=len(yearwords)<=6:return out,[{'page':page_number,'reason':'salient_year_columns_unresolved'}]
    centers=[(w['x0']+w['x1'])/2 for w in yearwords]
    boundaries=[centers[0]-35]+[(a+b)/2 for a,b in zip(centers,centers[1:])]+[10000]
    font=max(w['size'] for w in yearwords)
    default={'unit':'metric_ton' if 'metric ton' in caption.lower() else None,
             'scale':'1000' if 'thousand' in caption.lower() else '1','material_basis':caption}
    group='';group_markers=[];group_x=0
    for row in rows:
        if row['top']<=header['top']+2:continue
        if re.match(r'^(Recycling|Import Sources|Tariff|Depletion|Government Stockpile|Prepared by)',row['text']):break
        labelwords=[w for w in row['words'] if w['x0']<boundaries[0]]
        label,markers=split_words(labelwords,font)
        cells=[[w for w in row['words'] if boundaries[i]<= (w['x0']+w['x1'])/2 <boundaries[i+1]] for i in range(len(centers))]
        if not any(cells):
            if label.endswith(':') or any(x in label for x in ['Production','Consumption','Price','Stocks']):group=label;group_markers=markers;group_x=min(w['x0'] for w in labelwords)
            continue
        if labelwords and group and min(w['x0'] for w in labelwords)<group_x+4:
            group='';group_markers=[]
        continuation=next((r for r in rows if 0<r['top']-row['top']<15 and r['text'].startswith('dollars per')),None)
        if continuation and 'Price' in label:
            tail,tail_markers=split_words(continuation['words'],font)
            label+=' '+tail;markers+=tail_markers
        if label.endswith('of apparent') and any(r['text'].strip()=='consumption' and 0<r['top']-row['top']<15 for r in rows):
            label += ' consumption'
        if not label: gaps.append({'page':page_number,'bbox':row['bbox'],'reason':'unlabelled_numeric_row'});continue
        for i,cell in enumerate(cells):
            parsed=value_cell(cell,font,dash)
            if parsed['status']=='unparsed':gaps.append({'page':page_number,'label':label,'year':yearwords[i]['text'],'reason':'unparsed_cell','raw':parsed['raw_cell']})
            header_markers=[w['text'] for w in header['words'] if w['size']<font*.8 and abs(w['x0']-yearwords[i]['x1'])<8]
            refs=markers+group_markers+parsed['markers']+header_markers
            out.append({'table':'salient_us_statistics','metric':(group+' '+label).strip(), 'geography':'United States',
                'reference_year':int(yearwords[i]['text']),'edition':edition,**unit_for(label,group,default),**parsed,
                'estimated':any(re.search(r'(?<!\w)e(?!\w)',m) for m in refs) or 'Estimated' in label,'revised':any(re.search(r'(?<!\w)r(?!\w)',m) for m in refs),
                'footnote_refs':sorted(set(x for m in refs for x in re.findall(r'\d+',m))),
                'page':page_number,'bbox':row['bbox'],'source_row':row['text'],
                'validation':'layout_columns_and_cell_syntax_checked'})
    return out,gaps


def world_table(rows,page_number,caption,edition,dash):
    start=next((i for i,r in enumerate(rows) if re.match(r'^World (?:Mine )?Production and Reserves',r['text'])),None)
    if start is None:return [],[]
    header=next((r for r in rows[start+1:] if len([w for w in r['words'] if re.fullmatch(r'20\d{2}',w['text'])])==2),None)
    if not header:return [],[{'page':page_number,'reason':'world_table_year_columns_unresolved'}]
    years=[w for w in header['words'] if re.fullmatch(r'20\d{2}',w['text'])]
    reserveword=next((w for r in reversed(rows[start+1:]) if 0<header['top']-r['top']<25 for w in r['words'] if w['text']=='Reserves'),None)
    if not reserveword:return [],[{'page':page_number,'reason':'reserve_column_unresolved'}]
    centers=[(w['x0']+w['x1'])/2 for w in years]+[(reserveword['x0']+reserveword['x1'])/2]
    bounds=[centers[0]-40]+[(a+b)/2 for a,b in zip(centers,centers[1:])]+[10000]
    font=max(w['size'] for w in years);out=[];gaps=[]
    for row in rows:
        if row['top']<=header['top']+2:continue
        if re.match(r'^(World Resources|Substitutes|eEstimated|e Estimated|U.S. Geological)',row['text']):break
        label,_=split_words([w for w in row['words'] if w['x0']<bounds[0]],font)
        if not label:continue
        cells=[[w for w in row['words'] if bounds[i]<= (w['x0']+w['x1'])/2 <bounds[i+1]] for i in range(3)]
        if not any(cells):continue
        for i,cell in enumerate(cells):
            parsed=value_cell(cell,font,dash)
            out.append({'table':'world_production_reserves','metric':'mine_production' if i<2 else 'reserves',
                'geography':label,'reference_year':int(years[i]['text']) if i<2 else None,
                'time_basis':'calendar_year' if i<2 else 'reported_in_edition; reserve_as_of_date_unverified',
                'edition':edition,'unit':'metric_ton' if 'metric ton' in caption.lower() else None,
                'scale':'1000' if 'thousand' in caption.lower() else '1','material_basis':caption,
                **parsed,'estimated':i<2 and (any(w['text']=='e' and w['size']<font*.8 for r in rows[start:] if r['top']<header['top'] for w in r['words']) or any(w['text']=='e' and w['size']<font*.8 and abs(w['x0']-years[i]['x1'])<8 for w in header['words'])),
                'footnote_refs':[x for m in parsed['markers'] for x in re.findall(r'\d+',m)],
                'page':page_number,'bbox':row['bbox'],'source_row':row['text'],
                'validation':'layout_columns_and_cell_syntax_checked'})
            if parsed['status']=='unparsed':gaps.append({'page':page_number,'reason':'world_cell_unparsed','raw':parsed['raw_cell']})
    return out,gaps


def stockpile_table(rows,page_number,dash):
    start=next((i for i,r in enumerate(rows) if r['text'].startswith('Government Stockpile')),None)
    if start is None:return []
    remaining=rows[start:]
    header=next((r for r in remaining if sum(w['text'].lower() in {'acquisitions','disposals'} for w in r['words'])==4),None)
    if header is None:return []
    cols=[w for w in header['words'] if w['text'].lower() in {'acquisitions','disposals'}]
    centers=[(w['x0']+w['x1'])/2 for w in cols]
    bounds=[centers[0]-35]+[(a+b)/2 for a,b in zip(centers,centers[1:])]+[10000]
    years=[int(w['text']) for r in remaining if r['top']<header['top'] for w in r['words'] if re.fullmatch(r'20\d{2}',w['text'])]
    if len(years)!=2:return []
    font=max(w['size'] for w in cols);out=[]
    for row in remaining:
        if row['top']<=header['top']+2:continue
        if row['text'].startswith(('Prepared by','U.S. Geological')):break
        label,markers=split_words([w for w in row['words'] if w['x0']<bounds[0]],font)
        if not label:continue
        for i,col in enumerate(cols):
            words=[w for w in row['words'] if bounds[i]<=(w['x0']+w['x1'])/2<bounds[i+1]]
            if not words:continue
            out.append({'material':label,'fiscal_year':years[i//2],'action':'potential_'+col['text'].lower(),
                'weight_basis':'gross_weight' if 'gross weight' in label.lower() else 'source_context_review_required',
                **value_cell(words,font,dash),'page':page_number,'bbox':row['bbox'],'source_row':row['text'],
                'interpretation':'plan_or_authority; not executed acquisition or disposal'})
    return out


def sections_from_pages(pages):
    sections=[]
    pattern=re.compile(r'^('+ '|'.join(re.escape(h) for h in HEADINGS)+r')(?:[^:]{0,30}):',re.M)
    for page in pages:
        text=page['text'];matches=list(pattern.finditer(text))
        for i,m in enumerate(matches):
            end=matches[i+1].start() if i+1<len(matches) else len(text)
            sections.append({'heading':m[1],'page':page['page'],'text':text[m.start():end].strip()})
    return sections


def narrative_evidence(sections,edition,mineral):
    developments=[];shares=[];assets=[];sector_links=[]
    for section in sections:
        text=section['text']
        sentences=re.split(r'(?<=[.;])\s+(?=[A-Z])',text.replace('\n',' '))
        for sentence in sentences:
            if re.search(r'\b(bann?ed|ban|quotas?|closed|opened|suspended|restarted|commissioned|cancelled|canceled|solicitation|restrictions?|revised)\b',sentence,re.I):
                dates=re.findall(r'\b(?:19|20)\d{2}\b',sentence)
                month=re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b',sentence)
                developments.append({'claim':sentence,'page':section['page'],'section':section['heading'],
                    'explicit_year_mentions':dates,'explicit_month_mentions':month,'event_date':None,
                    'review_status':'source_attributed_candidate; temporal_role_and_external_confirmation_required'})
            for name in re.findall(r'\b(?:[A-Z][\w–-]+\s+){1,5}(?:Mine|mine|Refinery|refinery|Project|project)\b',sentence):
                if name in {'World Mine','United States Mine'}:continue
                assets.append({'name':name,'role':'named_asset_mention','page':section['page'],'evidence':sentence,'ownership':'unresolved'})
        if section['heading']=='Import Sources':
            period=re.search(r'\((\d{4})[–-](\d{2,4})\)',text)
            period_value=None
            if period:
                end=period[2] if len(period[2])==4 else period[1][:2]+period[2]
                period_value={'start_year':int(period[1]),'end_year':int(end)}
            for match in re.finditer(r'([A-Z][A-Za-z ()–-]+|other),\s*(\d+(?:\.\d+)?)%',text):
                shares.append({'geography':match[1].strip(),'share_percent':match[2],'reference_period':period_value,
                    'material_form_context':text.split(':',2)[1].strip() if text.count(':')>1 else None,
                    'page':section['page'],'source_text':text,'basis':'share_of_reported_import_sources; not global production share'})
        if section['heading'] in {'Domestic Production and Use','Substitutes'}:
            for keyword,sector,subsector in [('batter','energy_storage','batteries'),('superalloy',None,'superalloys'),
                ('magnet',None,'magnets'),('prosthe',None,'prosthetics'),('semiconductor','semiconductors','semiconductors'),('robot','robotics','robotics')]:
                for sentence in sentences:
                    if keyword in sentence.lower():sector_links.append({'mineral':mineral,'sector_candidate':sector,
                        'application':subsector,'keyword':keyword,'source_claim':sentence,'page':section['page'],
                        'status':'application_context_only; sector_fit_and_company_exposure_unverified'})
    return developments,shares,assets,sector_links


def within_report_changes(stats):
    groups={}
    for cell in stats:
        if cell.get('reference_year') and cell['table']=='salient_us_statistics' and cell['status']=='numeric' and cell.get('unit'):
            groups.setdefault((cell['metric'],cell['geography'],cell['unit'],cell['scale'],cell['material_basis']),[]).append(cell)
    result=[]
    for key,cells in groups.items():
        ordered=sorted(cells,key=lambda c:c['reference_year'])
        a,b=ordered[-2:] if len(ordered)>=2 else (None,None)
        if not a or b['reference_year']-a['reference_year']!=1:continue
        delta=Decimal(b['value'])-Decimal(a['value'])
        result.append({'metric':key[0],'geography':key[1],'unit':key[2],'scale':key[3],
            'from_year':a['reference_year'],'to_year':b['reference_year'],'from_value':a['value'],'to_value':b['value'],
            'absolute_change':str(delta),'absolute_change_unit':'percentage_points' if key[2]=='percent' else key[2], 'relative_change_percent':str((delta/Decimal(a['value'])*100).quantize(Decimal('.01'))) if Decimal(a['value']) else None,
            'estimated_inputs':[a.get('estimated'),b.get('estimated')],'source_pages':[a['page'],b['page']],
            'interpretation':'arithmetic_change_in_reported_series; definitions_and_materiality_require_review'})
    return result


def parse_report(raw,url):
    edition,mineral=document_identity(url)
    require(raw.startswith(b'%PDF-') and len(raw)<=16*1024*1024,'usgs_invalid_or_oversize_pdf')
    pages=[];stats=[];gaps=[];row_index=[];stockpile_values=[]
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        require(0<len(pdf.pages)<=20,'usgs_unexpected_page_count')
        for i,page in enumerate(pdf.pages):
            text=page.extract_text() or '';rows=lines(page)
            pages.append({'page':i+1,'text':text,'layout_text':page.extract_text(layout=True),'width':page.width,'height':page.height})
            row_index.extend({'page':i+1,'text':r['text'],'bbox':r['bbox']} for r in rows)
        full='\n'.join(p['text'] for p in pages)
        require(mineral.upper() in full.upper(),'usgs_mineral_title_mismatch')
        caption=next((m[0] for m in [re.findall(r'\(Data in[^\n]+',full)] if m),'unit_caption_unresolved')
        dash='zero' if re.search(r'[—–]\s*Zero\.',full,re.I) else None
        for i,page in enumerate(pdf.pages):
            rows=lines(page)
            stockpile_values.extend(stockpile_table(rows,i+1,dash))
            for parser in [stats_table,world_table]:
                cells,issues=parser(rows,i+1,caption,edition,dash);stats.extend(cells);gaps.extend(issues)
    if any(len(p['text'].strip())<100 for p in pages):gaps.append({'reason':'ocr_needed_or_sparse_text'})
    for cell in stats:
        if cell.get('unit') is None:gaps.append({'reason':'cell_unit_unresolved','metric':cell['metric'],'page':cell['page']})
    if not stats:gaps.append({'reason':'no_validated_statistics_extracted'})
    sections=sections_from_pages(pages)
    footnotes=[r for r in row_index if re.match(r'^(?:\d{1,2}\s+[A-Z]|e\s*Estimated|NA\s+Not available)',r['text'])]
    dev,shares,assets,links=narrative_evidence(sections,edition,mineral)
    publication=re.search(r'Mineral Commodity Summaries,\s*([A-Za-z]+)\s+(20\d{2})',full)
    pub={'value':publication[2]+'-'+str(datetime.strptime(publication[1],'%B').month).zfill(2),'precision':'month','basis':'report_footer'} if publication else None
    tariff_rows=[{**r,'tariff_code':m[0],'rate_text':r['text'][m.end():].strip(),'status':'historical_reported_schedule; not current applied tariff advice'} for r in row_index if (m:=re.search(r'\b\d{4}\.\d{2}\.\d{4}\b',r['text']))]
    stockpile=[s for s in sections if s['heading']=='Government Stockpile']
    if publication:require(int(publication[2])==edition,'usgs_report_edition_mismatch')
    return {'version':VERSION,'report_id':digest([url]),'report_version_id':digest([url,hashlib.sha256(raw).hexdigest()]),
        'edition':edition,'mineral':mineral,'source_url':url,'pdf_sha256':hashlib.sha256(raw).hexdigest(),
        'page_count':len(pages),'pages':pages,'sections':sections,'layout_rows':row_index,
        'publication':pub,'revision_date':None,'default_unit_caption':caption,'footnotes':footnotes,
        'symbol_definitions':{'dash':dash,'NA':'not_available','W':'withheld','e':'estimated'},
        'statistics':stats,'within_report_changes':within_report_changes(stats),
        'supply_chain':{'import_source_shares':shares,'source_sections':[s for s in sections if s['heading'] in {'Domestic Production and Use','Events, Trends, and Issues','Recycling','Import Sources','World Resources','Substitutes'}],
            'tariff_rows':tariff_rows,'stockpile_values':stockpile_values,'stockpile_sections':stockpile,'stockpile_note':'potential acquisitions/disposals are not completed transactions; fiscal years and gross weight stay explicit'},
        'development_candidates':dev,'entity_candidates':assets,'sector_application_links':links,
        'gaps':gaps,'numeric_extraction':'geometry_and_cell_syntax_validated; source_estimates_and_footnotes_require_review',
        'status':'review_required' if gaps else 'enriched','point_in_time_eligible':False}


def compare_editions(current,previous):
    if not previous:return {'status':'previous_edition_unavailable','revisions':[],'new_reference_years':[]}
    require(previous['mineral']==current['mineral'] and previous['edition']<current['edition'],'usgs_invalid_comparison_edition')
    def key(s):return (s['table'],s['metric'],s['geography'],s.get('reference_year'),s.get('unit'),s.get('scale'),s.get('time_basis'))
    old={key(s):s for s in previous['statistics']};revisions=[];new=[];unmatched=[]
    old_years={s.get('reference_year') for s in previous['statistics']}
    for cell in current['statistics']:
        prior=old.get(key(cell))
        if prior is None:
            if cell.get('reference_year') and cell['reference_year'] not in old_years:new.append({'metric':cell['metric'],'geography':cell['geography'],'reference_year':cell['reference_year']})
            else:unmatched.append({'metric':cell['metric'],'geography':cell['geography'],'reference_year':cell.get('reference_year')})
            continue
        # Reserve snapshots have no evidenced common as-of date: do not label their movement a historical revision.
        if cell.get('reference_year') is None:continue
        if (cell['value'],cell['status'],cell.get('estimated')) != (prior['value'],prior['status'],prior.get('estimated')):
            revisions.append({'metric':cell['metric'],'geography':cell['geography'],'reference_year':cell['reference_year'],
                'previous':{k:prior.get(k) for k in ['value','status','estimated','page','source_row']},
                'current':{k:cell.get(k) for k in ['value','status','estimated','page','source_row']},
                'unit':cell['unit'],'classification':'reported_series_revision_candidate; definition_and_footnote_review_required'})
    return {'status':'compared','previous_report_version_id':previous['report_version_id'],'previous_pdf_sha256':previous['pdf_sha256'],
            'previous_publication':previous['publication'],'revisions':revisions,'new_reference_years':new,'unmatched_series':unmatched,
            'availability_note':'Report vintages are distinct; retrieval today does not reconstruct historical availability.'}


def entity_mentions(report,directory):
    matches=[]
    for entity_type,id_field in [('companies','company_id'),('products','product_id')]:
        group=directory.get(entity_type,{})
        entities={e[id_field]:e for e in group.get(entity_type,[]) if e.get('review_status')=='verified' and not e.get('archived_at')}
        names=[(i,e['canonical_name']) for i,e in entities.items()]
        names += [(a[id_field],a['alias']) for a in group.get('aliases',[]) if a.get(id_field) in entities and a.get('review_status')=='verified']
        for identity,name in names:
            if len(name)<4 or len(name.split())==1:continue # generic single-word entities require a later contextual resolver
            pattern=re.compile(r'(?<!\w)'+re.escape(name)+r'(?!\w)',re.I)
            for page in report['pages']:
                for m in pattern.finditer(page['text']):
                    matches.append({'entity_type':entity_type[:-1] if entity_type=='products' else 'company',id_field:identity,
                        'matched_name':name,'page':page['page'],'offset':m.start(),'context':page['text'][max(0,m.start()-100):m.end()+150],
                        'basis':'verified_directory_exact_multiword_mention','role':'mention_only; ownership_and_product_exposure_unverified'})
    return {'status':'checked','matches':matches,'directory_sha256':digest(directory),
        'company_count':len(directory.get('companies',{}).get('companies',[])),
        'product_count':len(directory.get('products',{}).get('products',[])),
        'matched_at':now(),'historical_association':False,'admission':'unmatched names are review candidates; no registry writes'}


def directory_snapshot(client):
    if hasattr(client,'_usgs_directory'):return client._usgs_directory
    try:
        from rds_company_directory import read_directory
        data={'companies':read_directory('companies'),'products':read_directory('products')}
        key='operations/usgs-minerals/directories/'+digest(data)+'.json'
        write_json(client.store,key,data)
        result={'data':data,'snapshot_key':key,'checked_at':now()}
    except Exception as exc:
        result={'status':'directory_unavailable','error_type':type(exc).__name__,'matches':[],'checked_at':now()}
    client._usgs_directory=result
    return result


def enrich_report(raw,url,client,previous=None,directory=None):
    report=parse_report(raw,url)
    report['edition_comparison']=compare_editions(report,previous)
    snapshot=directory if directory is not None else directory_snapshot(client)
    report['entity_links']=entity_mentions(report,snapshot['data']) if 'data' in snapshot else snapshot
    if snapshot.get('snapshot_key'):report['entity_links']['snapshot_key']=snapshot['snapshot_key']
    report['event_candidates']=[{'type':'macro.statistics_release','key':report['report_id'],
        'content_version':report['report_version_id'],'publication':report['publication'],'review_status':'pending'}]
    if previous and report['edition_comparison']['revisions']:
        report['event_candidates'].append({'type':'macro.statistics_revision','key':digest([report['report_id'],previous['report_version_id']]),
            'content_version':report['report_version_id'],'review_status':'pending'})
    if report['edition_comparison']['status']!='compared':report['gaps'].append({'reason':'previous_edition_comparison_unavailable'})
    if report['entity_links'].get('status')!='checked':report['gaps'].append({'reason':'rds_directory_unavailable'})
    report['status']='review_required' if report['gaps'] else 'enriched'
    return report


def capture(raw,url,client,previous=None,directory=None,update_head=True):
    edition,mineral=document_identity(url)
    if previous is None:
        previous_url=url.replace('mcs'+str(edition),'mcs'+str(edition-1))
        try:
            prior_raw=client.get(previous_url)
            previous=parse_report(prior_raw,previous_url)
        except (SourceIssue,ValueError,RuntimeError) as exc:
            previous=None
    report=enrich_report(raw,url,client,previous,directory)
    headkey='operations/usgs-minerals/report-heads/'+digest(url)+'.json'
    head=client.store.get(headkey)
    prior=json.loads(head.body) if head else None
    report['same_edition_comparison']={'status':'first_observation_no_saved_baseline'}
    if prior:
        if prior['pdf_sha256']==report['pdf_sha256']:
            report['same_edition_comparison']={'status':'unchanged_pdf','previous_report_version_id':prior['report_version_id']}
        else:
            def observations(r):return [{'table':c['table'],'metric':c['metric'],'geography':c['geography'],
                'year':c.get('reference_year'),'value':c['value'],'status':c['status'],'unit':c['unit'],
                'estimated':c.get('estimated'),'footnote_refs':c['footnote_refs']} for c in r['statistics']]
            changed=digest(observations(prior))!=digest(observations(report))
            text_changed=digest([re.sub(r'\s+',' ',p['text']) for p in prior['pages']])!=digest([re.sub(r'\s+',' ',p['text']) for p in report['pages']])
            if changed or text_changed:
                report['event_candidates'].append({'type':'macro.statistics_revision','key':digest([report['report_id'],'same_edition_revision']),
                    'content_version':report['report_version_id'],'review_status':'pending; verify substantive source change and publication timing'})
            report['same_edition_comparison']={'status':'changed_pdf','statistics_changed':changed,'text_changed':text_changed,
                'previous_report_version_id':prior['report_version_id'],'review_status':'pending; changed_pdf_alone_is_not_material_event'}
    # Keep every full report version immutable; latest head is operational, not historical evidence.
    write_json(client.store,'operations/usgs-minerals/reports/'+report['report_version_id']+'/'+digest(report)+'.json',report)
    # Use captured head CAS: concurrent daily/backfill work must not silently overwrite a newer head.
    if update_head and (not prior or report['edition_comparison'].get('status')=='compared'):
        try:write_json(client.store,headkey,report,head.token if head else None)
        except __import__('collection_storage').Conflict:pass # next daily capture reconciles competing head updates
    return report
