from pathlib import Path
import hashlib,json
for root in [Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source')]:
 for name in ['regulatory_collection.py','additional_source_apis.py','specialist_inputs.py','public_source_capture.py','collection_alerts.py','constellation/gaps.py']:
  p=root/name
  if p.exists():print(json.dumps({'root':str(root),'file':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
