"""Stable query dimensions for gaps: date windows vary, company/topic scopes do not."""
import hashlib
import json
import re

DATE_KEYS={'start','end','year','period','realtime_end','fiscal_years','dateStart','dateEnd','mindate','maxdate','starttime','endtime','bgn_de','end_de','RecallDateStart','RecallDateEnd'}

def dimensions(value):
    if isinstance(value,dict):return {k:dimensions(v) for k,v in value.items() if k not in DATE_KEYS}
    if isinstance(value,list):return [dimensions(v) for v in value]
    if isinstance(value,str):
        value=re.sub(r'(?<!\d)20\d{2}[-/]\d{2}[-/]\d{2}(?!\d)','<date>',value)
        return re.sub(r'(?<!\d)20\d{6}(?!\d)','<date>',value)
    return value

def specialist_scope(window):
    parameters=(window.get('job') or {}).get('parameters',{})
    # Receipts without saved job dimensions cannot safely cancel another job's gap.
    identity=dimensions(parameters) if parameters else {'job_id':window.get('job_id','unknown')}
    suffix=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24]
    return '|'.join((window['source'],window.get('source_id',''),'specialist_historical',suffix))
