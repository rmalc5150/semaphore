"""Compact live worker checks, including effective limits and failure tails."""
from constellation.finish_aux_migration import remote,T3,M7

CODE='''import subprocess,json
def run(*args):
 r=subprocess.run(args,capture_output=True,text=True);return r.stdout.strip()
print('MEMORY',run('free','-m'));print('CPU',run('vmstat','1','3'))
failed=run('systemctl','list-units','--failed','--no-legend','--plain','optima-*.service','constellation-*.service')
print('FAILED',failed)
for line in failed.splitlines():
 parts=line.split();unit=next(x for x in parts if x.endswith('.service'))
 print('FAILURE_LOG',unit,run('journalctl','-u',unit,'-n','18','--no-pager'))
print('LIMITS',run('systemctl','show','optima-data.slice','constellation-workers.slice','-p','Id','-p','CPUQuotaPerSecUSec','-p','MemoryHigh','-p','MemoryMax','-p','MemoryCurrent'))
print('OOM',run('journalctl','-k','--since','30 minutes ago','--grep','oom-kill|Out of memory','-n','8','--no-pager'))
'''
def main():
 remote(M7,CODE)
 remote(T3,CODE)
if __name__=='__main__':main()
