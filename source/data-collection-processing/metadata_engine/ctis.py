"""Validate CTIS trial details and derived events against original API bytes."""
import json,re
from urllib.parse import urlsplit

class ProviderError(ValueError):pass

def require(ok,reason):
    if not ok:raise ProviderError(reason)

def validate(body,record,url):
    u=urlsplit(url);match=re.fullmatch(r'/ctis-public-api/retrieve/(\d{4}-\d{6}-\d{2}-\d{2})',u.path)
    require(u.scheme=='https' and u.netloc=='euclinicaltrials.eu' and match is not None and not u.query,'ctis_not_original_detail_endpoint')
    identity=match[1]
    try:detail=json.loads(body)
    except (ValueError,UnicodeError):raise ProviderError('ctis_invalid_detail_json')from None
    require(isinstance(detail,dict) and detail.get('ctNumber')==identity,'ctis_detail_identity_mismatch')
    auth=detail.get('authorizedApplication');require(isinstance(auth,dict),'ctis_missing_authorized_application')
    apps=auth.get('applicationInfo');require(isinstance(apps,list) and bool(apps) and all(isinstance(a,dict) for a in apps),'ctis_missing_application_details')
    payload=record.get('payload',{});data=payload.get('data',{});rid=record.get('source_record_id');kind=payload.get('record_type')
    link=urlsplit(record.get('source_url',''));require(link.scheme=='https' and link.netloc=='euclinicaltrials.eu' and link.path=='/ctis-public/view/'+identity,'ctis_record_url_mismatch')
    if kind=='clinical_trial':
        require(rid==identity and data.get('detail')==detail,'ctis_saved_detail_mismatch')
        require(isinstance(data.get('summary'),dict) and data['summary'].get('ctNumber')==identity,'ctis_summary_identity_mismatch')
    elif kind=='regulatory_event':
        require(isinstance(data.get('trial_summary'),dict) and data['trial_summary'].get('ctNumber')==identity,'ctis_summary_identity_mismatch')
        if 'application' in data:
            app=data['application'];require(isinstance(app,dict),'ctis_invalid_application')
            matches=[a for a in apps if a.get('id')==app.get('id')]
            require(len(matches)==1 and matches[0]==app and rid==f"{identity}:application:{app.get('id')}:submitted" and data.get('action')=='SUBMITTED','ctis_application_event_mismatch')
        else:
            decision=data.get('decision');require(isinstance(decision,dict),'ctis_invalid_decision')
            matches=[d for a in apps if a.get('id')==data.get('application_id') for d in a.get('decisions',[]) if isinstance(d,dict) and d.get('id')==decision.get('id')]
            require(len(matches)==1 and matches[0]==decision and rid==f"{identity}:decision:{decision.get('id')}",'ctis_decision_event_mismatch')
    else:raise ProviderError('ctis_unsupported_record_type')
    return {'provider':'EMA CTIS','ct_number':identity,'record_type':kind,'application_count':len(apps),'scope':'Original current public trial detail; events are matched subrecords, not full document downloads or historical vintages.'}
