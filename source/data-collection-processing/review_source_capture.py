#!/usr/bin/env python3
"""Capture bounded official-company source pages and test candidate publisher feeds."""
import json,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
ROOT=Path(__file__).resolve().parent
SOURCES=[
 ('Samsung Display','https://global.samsungdisplay.com/overview','semiconductors','official'),
 ('LG Display','https://www.lgdisplay.com/eng/company/info/outline/vision','semiconductors','official'),
 ('insitro','https://www.insitro.com/platform/','biotech','official'),
 ('Agility Robotics','https://www.agilityrobotics.com/company-overview','robotics','official'),
 ('Lightmatter','https://lightmatter.co/','semiconductors','official'),
 ('Antora Energy','https://www.antora.com/technology','energy_storage','official'),
 ('Form Energy','https://formenergy.com/technology/battery-technology/','energy_storage','official'),
 ('Robohub','https://robohub.org/feed/','robotics','feed'),
 ('EE Times','https://www.eetimes.com/feed/','semiconductors','feed'),
 ('pv magazine','https://www.pv-magazine.com/feed/','energy_storage','feed')]
def main():
 s=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=s.store();rows=[]
 out=ROOT/'reports/company-source-review';out.mkdir(exist_ok=True)
 for name,url,sector,kind in SOURCES:
  client=EvidenceClient(store,'company_review' if kind=='official' else 'people_rss');row={'name':name,'url':url,'sector':sector,'kind':kind,'observed_at':datetime.now(timezone.utc).isoformat()}
  try:
   raw=client.get(url);sha=hashlib.sha256(raw).hexdigest();(out/(sha+'.raw')).write_bytes(raw)
   row.update(status='captured',sha256=sha,bytes=len(raw),source_evidence=client.evidence)
   if kind=='feed':
    root=ET.fromstring(raw);row['feed_valid']=root.tag.rsplit('}',1)[-1] in {'rss','feed','RDF'}
  except Exception as exc:row.update(status='failed',error_type=type(exc).__name__,reason=getattr(exc,'code',None))
  rows.append(row);(out/'captures.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({k:v for k,v in row.items() if k not in ['source_evidence']}),flush=True)
if __name__=='__main__':main()
