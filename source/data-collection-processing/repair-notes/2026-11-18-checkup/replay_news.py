import os,sys,json,fcntl
from pathlib import Path
root=Path('/opt/constellation/capture-workers/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
import news_operations as n
cfg=n.load_json(root/'config/news-operations.json');daily=n.load_json(root/cfg['daily_config']);print('PROVIDERS',list(daily['providers']),flush=True)
from source_pauses import is_paused
assert is_paused('marketaux') and not is_paused('finlight'), 'verify owner pause before any API request'
sys.argv=['news_operations.py','--lane','daily'];print('NEWS_EXIT',n.main(),flush=True)
