"""Company-authored Bluesky publication events, backed by reviewed RDS identities."""
import re
from datetime import datetime,timezone
from people_social_collection import event_timestamp
from research_contract import digest

VERSION='bluesky-company-events-v1'
DID=re.compile(r'^did:(?:plc:[a-z2-7]{24}|web:[A-Za-z0-9.%:_-]+)$')
HANDLE=re.compile(r'^(?=.{3,253}$)[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z][a-zA-Z0-9-]*$')


def reviewed_accounts(company,identifiers):
    if company.get('archived_at'):return {'status':'archived','dids':[],'handles':[]}
    if company.get('review_status')!='verified':return {'status':'company_identity_review_required','dids':[],'handles':[]}
    if not company.get('collection_enabled'):return {'status':'company_collection_disabled','dids':[],'handles':[]}
    selected=[i for i in identifiers if i['company_id']==company['company_id'] and i.get('review_status')=='verified']
    dids=sorted({i['identifier_value'] for i in selected if i['namespace']=='bluesky_did'})
    handles=sorted({i['identifier_value'].lower().removeprefix('@') for i in selected if i['namespace']=='bluesky_handle'})
    if any(not DID.fullmatch(d) for d in dids) or any(not HANDLE.fullmatch(h) for h in handles):
        return {'status':'invalid_registry_account_identifier','dids':[],'handles':[]}
    return {'status':'reviewed_account_available' if dids or handles else 'account_identity_missing',
      'dids':dids,'handles':handles,'registry_identifiers':[i for i in selected if i['namespace'] in ('bluesky_did','bluesky_handle')]}


def development_candidates(text):
    """Review routes only: wording can describe plans, denials or another party."""
    rules={
      'product.launch':r'\b(?:launch(?:ed|ing)?|introducing|now available|released)\b',
      'business.partnership':r'\b(?:partnership|collaborat\w*|agreement|partnered)\b',
      'clinical.trial_update':r'\b(?:clinical trial|trial results|phase [1-4iv]+|enroll\w*)\b',
      'regulatory.decision':r'\b(?:approval|approved|clearance|authorization)\b',
      'finance.funding':r'\b(?:financing|funding|grant|raised)\b',
      'personnel.change':r'\b(?:appointed|new ceo|new cfo|stepping down|joins as)\b',
      'technology.release':r'\b(?:sdk|firmware|software release|version \d)\b'}
    out=[]
    for kind,pattern in rules.items():
        hits=list(re.finditer(pattern,text,re.I))
        if not hits:continue
        modality='negated_or_uncertain' if re.search(r"\b(?:not|no|never|denied|rumou?r|unconfirmed)\b",text,re.I) else 'future_or_conditional' if re.search(r'\b(?:will|plan(?:s|ned)?|expect\w*|aim\w*|may|could|would)\b',text,re.I) else 'company_reported_unverified'
        out.append({'candidate_type':kind,'modality':modality,'review_status':'pending_claim_and_entity_review',
          'matched_spans':[{'start':m.start(),'end':m.end(),'text':m.group()} for m in hits],
          'event_at':None,'product_ids':[],'promoted_to_material_event':False})
    return out


def post_event(item,did,company,observed_at):
    """The event is publication of a company communication, not proof of its claims."""
    if item.get('reason',{}).get('$type') in ('app.bsky.feed.defs#reasonRepost','app.bsky.feed.defs#reasonPin'):return None
    post=item.get('post') or {};author=post.get('author') or {};record=post.get('record') or {}
    if author.get('did')!=did:return None
    uri=post.get('uri') or '';cid=post.get('cid')
    if not uri.startswith('at://'+did+'/app.bsky.feed.post/') or not re.fullmatch(r'[A-Za-z0-9._~:-]+',uri.rsplit('/',1)[-1]) or not cid:
        raise ValueError('Invalid authored post identity')
    if record.get('$type')!='app.bsky.feed.post' or not isinstance(record.get('text'),str):raise ValueError('Invalid authored post record')
    created=event_timestamp(record.get('createdAt'));indexed=event_timestamp(post.get('indexedAt'))
    if created and datetime.fromisoformat(created['value'].replace('Z','+00:00'))>datetime.fromisoformat(observed_at.replace('Z','+00:00')):
        created=None
    links=[]
    for facet in record.get('facets',[]):
        for feature in facet.get('features',[]):
            if feature.get('$type')=='app.bsky.richtext.facet#link' and str(feature.get('uri','')).startswith(('http://','https://')):links.append(feature['uri'])
    external=(record.get('embed') or {}).get('external') or {}
    if str(external.get('uri','')).startswith(('http://','https://')):links.append(external['uri'])
    event_id='evt_'+digest(['S64','company.social_post_published',uri])
    return {'event_id':event_id,'event_version_id':digest([event_id,cid,company['company_id']]),
      'event_type':'company.social_post_published','source_id':'S64','company_ids':[company['company_id']],
      'product_ids':[],'person_ids':[],'author_did':did,'author_handle':author.get('handle'),
      'post_uri':uri,'post_cid':cid,'source_url':'https://bsky.app/profile/'+did+'/post/'+uri.rsplit('/',1)[-1],
      'statement':record['text'],'development_candidates':development_candidates(record['text']),'outbound_links':sorted(set(links)),
      'post_kind':'reply' if record.get('reply') else 'quote' if (record.get('embed') or {}).get('$type') in ('app.bsky.embed.record','app.bsky.embed.recordWithMedia') else 'original_post',
      'event_at':created,'provider_indexed_at':indexed,'claimed_created_at':record.get('createdAt'),'first_observed_at':observed_at,
      'event_status':'observed_publication','claim_status':'company_reported; underlying_claim_not_independently_verified',
      'account_binding_status':'reviewed_current_rds_identity; historical_account_ownership_not_established',
      'point_in_time_eligible':False,'specialist_dispatch_status':'pending_main_event_pipeline_integration',
      'semantic_event_status':'publication_only; material_milestone_requires_claim_extraction_correlation_and_review'}
