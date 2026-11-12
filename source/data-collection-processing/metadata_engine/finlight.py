"""Validate an article against the original Finlight provider response, not a request receipt."""
import json
from datetime import datetime
from urllib.parse import urlsplit
class ProviderError(ValueError):pass
def require(ok,reason):
 if not ok:raise ProviderError(reason)
def validate(body,record,url):
 require(url=='https://api.finlight.me/v2/articles','finlight_untrusted_api_url')
 try:data=json.loads(body)
 except (ValueError,UnicodeError):raise ProviderError('finlight_invalid_json')from None
 require(isinstance(data,dict)and data.get('status')=='ok'and isinstance(data.get('articles'),list),'finlight_not_article_response')
 require(type(data.get('page'))is int and data['page']>=1,'finlight_invalid_page')
 identity=record['source_record_id'];rows=[r for r in data['articles']if isinstance(r,dict)and r.get('link')==identity]
 require(len(rows)==1,'finlight_article_identity_missing_or_duplicate');row=rows[0];value=record.get('payload',{}).get('data',{})
 require(record.get('source_url')==identity and urlsplit(identity).scheme in ('http','https')and bool(urlsplit(identity).hostname),'finlight_article_url_mismatch')
 for key in ('link','title','publishDate','source','language'):
  require(isinstance(row.get(key),str)and bool(row[key])and value.get(key)==row[key],'finlight_article_field_mismatch:'+key)
 for key in ('summary','categories','countries','sentiment','confidence','images','companies'):
  if key in row:require(value.get(key)==row[key],'finlight_article_field_mismatch:'+key)
 try:stamp=datetime.fromisoformat(row['publishDate'].replace('Z','+00:00'));require(stamp.tzinfo is not None,'finlight_article_time_without_timezone')
 except (ValueError,TypeError):raise ProviderError('finlight_invalid_article_time')from None
 return {'provider':'finlight','article_identity':identity,'scope':'original provider article fields; publisher full text and historical availability are separate','page':data['page']}
