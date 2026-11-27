import subprocess,time
import repair_individual as r
r.OUT=r.ROOT/'repair-notes/2026-11-13-streaming-alerts'
deadline=time.monotonic()+700
while subprocess.check_output(['systemctl','show','optima-repair-news-1113.service','-p','ActiveState','--value'],text=True).strip()in ('active','activating'):
 if time.monotonic()>deadline:raise RuntimeError('news_repair_still_active; retain memory allowance for diagnosis')
 time.sleep(5)
result=r.execute('market-aapg',['repair-notes/2026-11-13-streaming-alerts/market_aapg.py'],480)
assert result['checkpoint_verified'], 'Preserve runtime for failed checkpoint inspection'
assert result['exit_code']==0, 'Inspect durable market repair log'
