import boto3,json,concurrent.futures
from pathlib import Path
from finlight_backfill import setup,earlier_archive
from botocore.exceptions import ClientError
p=Path(__file__).parent; c=json.loads(Path('config/collection-monitoring.json').read_text()); s=boto3.client('s3'); b=c['bucket']
f,cfg,prim=setup(); early,_,old=earlier_archive(f,cfg)
research='constellation-backfill/research-feeds/v1/'
pat='operations/patents/global-backfill/streams/d5548c10ab24a442ae7b6c5f05ed3e283f32a1e1e29b0662b74abdd80f903b96/'
keys={'research-control':research+'control.json','openalex-progress':research+'progress/openalex_scholarly_graph/snapshot.json','kaken-progress':research+'progress/japan_kaken_funded_research/historical.json','kaken-2016':research+'checkpoints/japan_kaken_funded_research/historical/fy-2016.json','finlight-history-probe':early['earlier_archive']['history_evidence'],'finlight-athena-proof':'operations/news/history_probes/8108d2f93270ab72e45d20ca647d0c98d28609630e353c01b7a4dd5fedfdcdb8.json','finlight-progress':old+'/collection.json','finlight-publication':old+'/publication.json','patents-progress':pat+'progress.json','patents-publication':pat+'athena-publication/progress.json'}
def read(item):
 n,k=item
 try:
  d=json.loads(s.get_object(Bucket=b,Key='research-data/'+k)['Body'].read());(p/(n+'.json')).write_text(json.dumps(d,indent=2));return n,k,{x:(len(v) if isinstance(v,list) else v) for x,v in d.items() if not isinstance(v,dict)}
 except ClientError as e: return n,k,e.response['Error']['Code']
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for row in pool.map(read,keys.items()): print(str(row)[:1000])
