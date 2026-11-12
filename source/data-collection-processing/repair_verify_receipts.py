"""Read back repaired publication evidence and check actual Athena query status."""
import hashlib,json,time
from pathlib import Path
import boto3
from collection_storage import StorageSettings
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'repair-notes/2026-10-21-individual-replays'

def main():
    store=StorageSettings.load(ROOT/'config/collection-storage.s3.json').store()
    athena=boto3.client('athena',region_name='us-east-1')
    rows=[]
    for file in sorted(OUT.glob('*.log')):
        captures={}
        for line in file.read_text(errors='replace').splitlines():
            try:event=json.loads(line)
            except ValueError:continue
            if isinstance(event,dict) and event.get('job_id') and event.get('capture'):
                captures[event['job_id']]=event
        for identity,event in captures.items():
            result={'step':file.stem,'job_id':identity,'capture':event['capture']}
            obj=store.get('operations/specialists/publication-receipts/'+identity+'.json')
            if obj:
                receipt=json.loads(obj.body)
                evidence=store.get(receipt['verification_key'])
                assert evidence and hashlib.sha256(evidence.body).hexdigest()==receipt['verification_sha256']
                assert event['capture']['manifest'] in receipt['manifests']
                qid=receipt['query']['query_id']
                query=athena.get_query_execution(QueryExecutionId=qid)['QueryExecution']
                assert query['Status']['State']=='SUCCEEDED',query['Status']
                result['athena']={'status':'verified','query_id':qid,'rows':receipt['query']['rows'],'receipt':receipt}
                sql="SELECT * FROM optima_specialist_inputs.source_observations_windows WHERE window_id='"+identity+"' LIMIT 1"
                sample_id=athena.start_query_execution(QueryString=sql,WorkGroup='optima-specialist-inputs',ResultConfiguration={'OutputLocation':'s3://data-collection-059416028963-us-east-1-an/research-data/athena-results/specialists/'},ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId']
                for _ in range(60):
                    state=athena.get_query_execution(QueryExecutionId=sample_id)['QueryExecution']['Status']
                    if state['State'] in {'SUCCEEDED','FAILED','CANCELLED'}:break
                    time.sleep(1)
                assert state['State']=='SUCCEEDED',state
                sample=athena.get_query_results(QueryExecutionId=sample_id)['ResultSet']
                result['athena']['sample_query_id']=sample_id
                result['athena']['sample']=sample

            else:result['athena']={'status':'not_yet_verified'}
            rows.append(result)
    (OUT/'athena-receipts.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps([{'step':r['step'],'capture_status':r['capture']['status'],'athena_status':r['athena']['status'],'query_id':r['athena'].get('sample_query_id')} for r in rows]))
if __name__=='__main__':main()
