"""Exact native NASA/arXiv records and scoped public original documents."""
import hashlib,io,json,re,xml.etree.ElementTree as ET
from urllib.parse import urlsplit
from functools import lru_cache

@lru_cache(maxsize=2)
def decode(raw):return json.loads(raw)

def validate_arxiv(raw,record):
 from metadata_engine.evidence import RawFailure
 root=ET.fromstring(raw);ns={'a':'http://www.w3.org/2005/Atom'};data=record['payload']['data'];rid=record['source_record_id']
 candidates=[]
 for node in root.findall('a:entry',ns):
  row={field:node.findtext('a:'+field,namespaces=ns)for field in ('id','title','summary','published','updated')}
  row['authors']=[v.findtext('a:name',namespaces=ns)for v in node.findall('a:author',ns)];row['categories']=[v.get('term')for v in node.findall('a:category',ns)]
  if row['id']==rid:candidates.append(row)
 if len(candidates)!=1 or candidates[0]!=data:raise RawFailure('arxiv_original_metadata_mapping_mismatch')
 if not re.fullmatch(r'https?://arxiv.org/abs/(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})v\d+',rid):raise RawFailure('arxiv_versioned_identity_missing')
 return {'provider':'arXiv native Atom','record_type':'publication_abstract_record','scope':'Exact returned versioned citation/abstract metadata and complete original Atom response; article full text and supplements are not collected.'}

def validate_nasa(raw,record):
 from metadata_engine.evidence import RawFailure
 data=record['payload']['data'];d=decode(raw);day=data['date'].replace('-','');values=d['properties']['parameter'];expected={k:v[day]for k,v in values.items()}
 if data['provider_values']!=expected or data['header']!=d['header']or data['parameters']!=d['parameters']:raise RawFailure('nasa_original_daily_measurement_mismatch')
 return {'provider':'NASA POWER','record_type':'weather_daily_measurement','scope':'Exact daily provider values, native units, fill flags and original point response; eight configured reference cells, current vintage.'}

def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure
 source=record['source'];errors=[]
 for ref in record['payload'].get('source_evidence',[]):
  key=ref.get('key')
  if not key and ref.get('s3_uri'):key=urlsplit(ref['s3_uri']).path.lstrip('/')
  if not key or not ref.get('sha256'):continue
  key=key if key.startswith('research-data/')else'research-data/'+key;url=ref.get('source_url','');u=urlsplit(url)
  if u.scheme!='https'or u.hostname not in (['export.arxiv.org']if source=='arxiv'else['power.larc.nasa.gov']):continue
  raw=object_bytes(s3,bucket,key,expected=ref['sha256'])
  try:info=validate_arxiv(raw,record)if source=='arxiv'else validate_nasa(raw,record)
  except(ValueError,KeyError,TypeError,ET.ParseError)as error:errors.append(str(error));continue
  return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'origin':'first_party_source','source_url':url,'retrieved_at':ref.get('retrieved_at'),'validation':info}]
 raise RawFailure(errors[0]if errors else'original_native_record_missing')
