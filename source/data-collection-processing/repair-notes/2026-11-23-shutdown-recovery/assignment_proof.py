import os,sys,json,subprocess
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root))
from collection_health_exporter import json_reports
u='optima-m7-capture-assignments-reviewed-historical.service';reports,events,latest=json_reports(u)
for r in reports[-1:]:print('ASSIGNMENT_PROOF',json.dumps({'at':r['at'],'status':r['value'].get('status'),'completed_scopes':r['value'].get('completed_scopes'),'reviewed_scope_only':r['value'].get('reviewed_scope_only')}))
print(subprocess.run(['systemctl','show',u,'-p','Result','-p','ExecMainStatus','-p','ActiveState'],capture_output=True,text=True).stdout)
