"""Raise m7 worker burst limits while retaining a shared memory budget."""
from constellation.finish_aux_migration import remote,M7

def main():
 remote(M7,'''from pathlib import Path
import subprocess,json,os
base=Path('/etc/systemd/system');mem_kib=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')));mem=mem_kib*1024
maximum=int(mem*.89);high=int(mem*.80)
def run(args):return subprocess.check_output(args,text=True).strip()
before={'mem_total':mem,'shared':run(['systemctl','show','constellation-workers.slice','-p','MemoryMax','-p','MemoryHigh','-p','CPUQuotaPerSecUSec'])}
run(['systemctl','set-property','constellation-workers.slice','CPUQuota=200%','MemoryHigh='+str(high),'MemoryMax='+str(maximum),'MemorySwapMax=0'])
units=run(['systemctl','list-unit-files','--type=service','--no-legend','--plain','optima-*.service','constellation-backfill@.service','constellation-legacy-worker@.service','constellation-public-worker@.service'])
configured=[]
for line in units.splitlines():
 unit=line.split()[0]
 if not (unit.startswith('optima-') or '@.service' in unit):continue
 if 'metadata' in unit:limit=768*1024**2;weight=150
 elif 'publication' in unit:limit=3*1024**3;weight=100
 elif 'backfill@' in unit:limit=512*1024**2;weight=75
 elif 'public-worker@' in unit:limit=768*1024**2;weight=75
 elif 'legacy-worker@' in unit:limit=2*1024**3;weight=75
 else:
  current=run(['systemctl','show',unit,'-p','MemoryMax','--value'])
  limit=min(3*1024**3,max(512*1024**2,int(current)*5//4 if current.isdigit()else 1024**3));weight=100
 folder=base/(unit+'.d');folder.mkdir(exist_ok=True)
 (folder/'zzzz-capacity.conf').write_text('[Service]\\nSlice=constellation-workers.slice\\nCPUQuota=200%\\nCPUWeight='+str(weight)+'\\nMemoryHigh='+str(limit*9//10)+'\\nMemoryMax='+str(limit)+'\\nMemorySwapMax=0\\n')
 configured.append((unit,limit,weight))
run(['systemctl','daemon-reload'])
# Change limits live without interrupting a collector or its provider request.
active=run(['systemctl','list-units','--all','--plain','--no-legend','--type=service','optima-*.service','constellation-backfill@*.service','constellation-legacy-worker@*.service','constellation-public-worker@*.service'])
applied=[]
for line in active.splitlines():
 unit=line.split()[0];template=unit.split('@')[0]+'@.service'if '@'in unit else unit
 match=next((x for x in configured if x[0]==template),None)
 if not match:continue
 _,limit,weight=match
 run(['systemctl','set-property',unit,'CPUQuota=200%','CPUWeight='+str(weight),'MemoryHigh='+str(limit*9//10),'MemoryMax='+str(limit),'MemorySwapMax=0'])
 applied.append(unit)
path=Path('/opt/constellation/config/constellation-infrastructure.json');cfg=json.loads(path.read_text());cfg.setdefault('worker_pool',{})['admission_memory_high_gib']=round(high/1024**3-.25,2)
tmp=path.with_suffix('.capacity');tmp.write_text(json.dumps(cfg,indent=2)+'\\n');os.chown(tmp,1000,1000);tmp.replace(path)
receipt={'before':before,'shared_memory_high':high,'shared_memory_max':maximum,'admission_memory_high_gib':cfg['worker_pool']['admission_memory_high_gib'],'configured_services':len(configured),'live_limits_updated':applied,'placement_note':'Services already outside the shared slice enter it on their next normal invocation.'}
Path('/opt/constellation/tmp/m7-capacity-receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
print(run(['free','-m']))
''')
if __name__=='__main__':main()
