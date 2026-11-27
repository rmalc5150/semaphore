import json,boto3
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/2026-11-16'
rows=json.load(open(p/'replay-results.json'))['outcomes']+json.load(open(p/'second-initial-results.json'));s.put_object(Bucket=b,Key=base+'/ready-results.json',Body=json.dumps({'outcomes':rows}).encode(),ServerSideEncryption='AES256')
script=(p/'publish_coverage.py').read_text().replace("base+'/replay-results.json'","base+'/ready-results.json'").replace("base+'/coverage-publication-results.json'","base+'/all-publication-results.json'")
s.put_object(Bucket=b,Key=base+'/all-publish.py',Body=script.encode(),ServerSideEncryption='AES256')
launch=(p/'launch_publication.py').read_text().replace("f=p/'publish.py'","f=p/'all-publish.py'").replace('2026-11-16/publish.py','2026-11-16/all-publish.py').replace('optima-checkup-1116-coverage-publication','optima-checkup-1116-all-publication').replace("p/'publish.log'","p/'all-publish.log'")
(p/'launch_all_publication.py').write_text(launch)
