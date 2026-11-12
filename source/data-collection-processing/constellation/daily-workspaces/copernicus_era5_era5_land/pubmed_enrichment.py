"""Evidence-linked PubMed interpretation; publication is not a dated clinical milestone."""
import re
import xml.etree.ElementTree as ET
from datetime import date

VERSION = 'pubmed-evidence-context-v1'


def text(node):
    return ' '.join(''.join(node.itertext()).split()) if node is not None else ''


def date_fact(node, basis):
    if node is None:
        return None
    year, month, day = node.findtext('Year'), node.findtext('Month'), node.findtext('Day')
    result = {'basis':basis,'source_text':text(node),'value':None,'precision':'unspecified'}
    if not year or not year.isdigit():
        return result
    if month and not month.isdigit():
        months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
        month = months.get(month.lower()[:3])
    try:
        if month and day:
            result.update(value=date(int(year),int(month),int(day)).isoformat(),precision='day')
        elif month:
            date(int(year),int(month),1)
            result.update(value=f'{int(year):04d}-{int(month):02d}',precision='month')
        else:
            result.update(value=year,precision='year')
    except ValueError:
        pass
    return result


def enrich(article_xml, expected_pmid=None):
    root = ET.fromstring(article_xml)
    if root.tag == 'PubmedBookArticle':
        pmid = root.findtext('BookDocument/PMID')
        if not pmid or (expected_pmid and str(expected_pmid) != pmid):
            raise ValueError('pubmed_primary_pmid_mismatch')
        return {'version':VERSION,'pmid':pmid,'title':text(root.find('BookDocument/ArticleTitle')),
            'study_design':'book_record_needs_review','abstract_sections':[], 'key_takeaway':None,
            'publication_event':{'type':'book_record','date':None,'underlying_clinical_event_date':None},
            'quality_flags':[{'code':'book_record_needs_review','detail':'Raw book record retained; no primary trial finding inferred.'}],
            'interpretation_status':'record_type_needs_review','company_product_person_ids_assigned':False}
    pmid = root.findtext('./MedlineCitation/PMID')
    if not pmid or (expected_pmid and str(expected_pmid) != pmid):
        raise ValueError('pubmed_primary_pmid_mismatch')
    article = root.find('./MedlineCitation/Article')
    if article is None:
        raise ValueError('pubmed_article_missing')
    title = text(article.find('ArticleTitle'))
    types = [text(n) for n in article.findall('PublicationTypeList/PublicationType')]
    sections = [{'label':n.get('Label'),'category':n.get('NlmCategory'),'text':text(n),
        'source_path':f'MedlineCitation/Article/Abstract/AbstractText[{i+1}]'}
        for i,n in enumerate(article.findall('Abstract/AbstractText'))]
    # Parse inline structured abstracts without inventing sections or facts.
    if len(sections) == 1 and not sections[0]['label']:
        value = sections[0]['text']
        matches = list(re.finditer(r'\b(Objectives?|Methods?|Results?|Conclusions?)\s*:',value,re.I))
        if len(matches) >= 3:
            sections = [{'label':m.group(1).upper(),'category':m.group(1).upper(),'text':value[m.end():matches[i+1].start() if i+1<len(matches) else len(value)].strip(),
                'source_path':'MedlineCitation/Article/Abstract/AbstractText[1]',
                'source_character_span':[m.end(), matches[i+1].start() if i+1<len(matches) else len(value)]}
                for i,m in enumerate(matches)]
    body = ' '.join(s['text'] for s in sections)
    combined = title + ' ' + body
    lower = combined.lower()
    review = any(t in ('Review','Systematic Review','Meta-Analysis') for t in types)
    flags = []
    if 'mendelian randomization' in lower or 'mendelian randomisation' in lower:
        design, event = 'genetic_causal_inference','genetic_analysis_report_published'
        if 'Randomized Controlled Trial' in types:
            flags.append({'code':'indexing_design_conflict','detail':'Randomized Controlled Trial tag conflicts with the stated Mendelian randomization design; do not treat genetic randomization as a treatment trial.'})
    elif re.search(r'closed due to poor recruitment|failed to meet recruitment goals',body,re.I):
        design,event='trial_report_with_recruitment_failure','recruitment_failure_report_published'
        flags.append({'code':'recruitment_failure','detail':'Recruitment failure limits efficacy interpretation; publication date is not the study closure date.'})
    elif review:
        design,event='evidence_synthesis','evidence_synthesis_published'
    elif any(t.startswith(('Clinical Trial','Controlled Clinical Trial','Randomized Controlled Trial')) for t in types):
        design,event='clinical_study_report','clinical_study_report_published'
    elif 'Letter' in types:
        design,event='letter','letter_published'
    else:
        design,event='unclassified_article','article_published'
        flags.append({'code':'design_needs_review','detail':'Publication metadata alone does not establish a primary trial report.'})
    abstracts_without_registration = ' '.join(s['text'] for s in sections if not re.search(r'trial registration',s['label'] or '',re.I))
    methods = [s for s in sections if re.search(r'method',s['label'] or '',re.I)]
    findings = [s for s in sections if re.search(r'result|conclu|data synthesis',s['label'] or '',re.I)]
    conclusions = [s for s in sections if re.search(r'conclu',s['label'] or '',re.I)]
    takeaway = None
    if conclusions:
        takeaway = {'text':conclusions[-1]['text'],'method':'author_conclusion_extract','attribution':'authors',
            'independent_assessment':False,'source':conclusions[-1]}
    elif sections:
        # No arbitrary sentence is promoted as the paper's conclusion.
        flags.append({'code':'unstructured_abstract_needs_summary_review','detail':'Abstract is present but has no explicit conclusion section; a concise paraphrase needs review.'})
    else:
        flags.append({'code':'abstract_missing','detail':'No findings or outcome direction can be inferred from the title; seek original full text.'})
    for code, pattern, detail in (
        ('exploratory_language',r'\bexploratory\b','Exploratory findings should not be promoted as confirmatory evidence.'),
        ('retrospective_registration',r'retrospectively registered','The authors explicitly describe retrospective trial registration.'),
        ('comparative_evidence_gap',r'head.to.head.*(?:required|needed)|appropriate matching of populations','Comparator selection or direct comparative evidence remains a limitation.'),
        ('additional_studies_needed',r'larg[e,r]*.*(?:trials|studies).*needed|further studies.*needed','The authors state that additional studies are needed.')):
        if re.search(pattern,body,re.I):
            flags.append({'code':code,'detail':detail})
    trial_links = {}
    def link(identifier,role,path,context):
        trial_links.setdefault(identifier,[]).append({'role':role,'source_path':path,'context':context})
    for bank in article.findall('DataBankList/DataBank'):
        if 'clinicaltrials' in text(bank.find('DataBankName')).lower():
            for acc in bank.findall('AccessionNumberList/AccessionNumber'):
                for identifier in re.findall(r'\bNCT\d{8}\b',text(acc)):
                    link(identifier,'declared_registration','MedlineCitation/Article/DataBankList',text(acc))
    for section in sections:
        for identifier in re.findall(r'\bNCT\d{8}\b',section['text']):
            role='trial_mentioned_in_abstract'
            if not review and (re.search(r'registr',section['label'] or '',re.I) or
                    re.search(r'(?:registered|registration|identifier|TRN).{0,100}'+identifier,section['text'],re.I)):
                role='declared_registration'
            link(identifier,role,section['source_path'],section['text'])
    for i,ref in enumerate(root.findall('./PubmedData/ReferenceList/Reference')):
        for identifier in re.findall(r'\bNCT\d{8}\b',text(ref)):
            link(identifier,'reference_only',f'PubmedData/ReferenceList/Reference[{i+1}]',text(ref))
    identifiers = {n.get('IdType'):text(n) for n in root.findall('./PubmedData/ArticleIdList/ArticleId')}
    dates = [date_fact(n,'electronic_publication' if n.get('DateType')=='Electronic' else 'article_date_'+str(n.get('DateType')))
             for n in article.findall('ArticleDate')]
    dates += [date_fact(article.find('Journal/JournalIssue/PubDate'),'journal_issue_publication')]
    dates += [date_fact(n,'pubmed_history_'+str(n.get('PubStatus'))) for n in root.findall('./PubmedData/History/PubMedPubDate')]
    dates = [d for d in dates if d]
    publication = next((d for d in dates if d['basis']=='electronic_publication' and d['value']),None)
    publication = publication or next((d for d in dates if d['basis']=='journal_issue_publication' and d['value']),None)
    authors = []
    for n in article.findall('AuthorList/Author'):
        authors.append({'name':' '.join(v for v in (n.findtext('ForeName'),n.findtext('LastName')) if v) or text(n.find('CollectiveName')),
            'identifiers':[{'source':i.get('Source'),'value':text(i)} for i in n.findall('Identifier')],
            'affiliations':[text(a) for a in n.findall('AffiliationInfo/Affiliation')],
            'affiliation_role':'publication_author_affiliation_not_trial_sponsorship_or_current_employment'})
    corrections=[{'relation':n.get('RefType'),'pmid':n.findtext('PMID'),'note':text(n.find('Note'))}
                 for n in root.findall('./MedlineCitation/CommentsCorrectionsList/CommentsCorrections')]
    if any('Retract' in t for t in types) or any(n['relation'] in ('RetractionIn','RetractionOf') for n in corrections):
        flags.append({'code':'retraction_related','detail':'Inspect the original correction/retraction relationship before using findings.'})
    return {'version':VERSION,'pmid':pmid,'title':title,'publication_types':types,'study_design':design,
        'classification_method':'conservative_rules_with_source_metadata','abstract_sections':sections,
        'methods_evidence':methods,'findings_evidence':findings,'key_takeaway':takeaway,
        'interpretation_status':'abstract_missing' if not sections else 'author_conclusion_extracted' if takeaway else 'summary_review_needed',
        'publication_event':{'type':event,'date':publication,'underlying_clinical_event_date':None,
            'claim_scope':'Publication of this report; not trial completion, approval, first disclosure or independent replication.'},
        'dates':dates,'identifiers':identifiers,
        'trial_links':[{'trial_id':identifier,'evidence':links,'identity_status':'source_link_not_verified_cross_record_join'} for identifier,links in sorted(trial_links.items())],
        'authors':authors,'funding':[{'grant_id':n.findtext('GrantID'),'agency':n.findtext('Agency'),'country':n.findtext('Country')} for n in article.findall('GrantList/Grant')],
        'conflict_of_interest_statement':text(root.find('./MedlineCitation/CoiStatement')) or None,
        'substances':[{'name':text(n.find('NameOfSubstance')),'vocabulary_id':n.find('NameOfSubstance').get('UI'),'registry_number':n.findtext('RegistryNumber'),
                      'entity_status':'source_term_not_resolved_product'} for n in root.findall('./MedlineCitation/ChemicalList/Chemical') if n.find('NameOfSubstance') is not None],
        'correction_relationships':corrections,'quality_flags':flags,
        'full_text_candidate':{'pmcid':identifiers.get('pmc'),'status':'not_retrieved','rights_or_programmatic_access_confirmed':False},
        'journal_country_is_not_trial_country':True,'source_xml_sha256':__import__('hashlib').sha256(article_xml.encode()).hexdigest(),
        'company_product_person_ids_assigned':False}
