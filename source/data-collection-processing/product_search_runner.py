"""Check missing input without taking shared capture/RAM locks or paid API calls."""
import json,os,sys
from pathlib import Path

def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if args[:1]==['--']:args=args[1:]
    config=json.loads((Path(__file__).resolve().parent/'config/product-search-daily.json').read_text())
    mode=config.get('directory',{}).get('mode')
    if mode=='metadata_engine':
        from product_search_directory import read_products
        if not read_products()['products']:
            config={**config,'directory':{'mode':'pending_registry','reason':'No named product entities exist in the Constellation metadata registry yet.','upstream':'metadata_engine.entities','scope':'all_products'}}
            mode='pending_registry'
    if mode=='pending_registry':
        from product_search_daily import execute
        result=execute(config,write_local_report=False)
        assert result['status']=='pending_dependency' and result['requests_made']==0
        print(json.dumps(result),flush=True);return 0
    if not args:raise RuntimeError('supervised product-search command required')
    os.execvp(args[0],args)
if __name__=='__main__':raise SystemExit(main())
