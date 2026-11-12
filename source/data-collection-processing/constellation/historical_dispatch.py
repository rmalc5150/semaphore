"""Keep validated historical routes queued; no payload executes on the controller."""
import json
from constellation.control import Control
from constellation.legacy_dispatch import dispatch
from constellation.legacy_routes import manifest

def main():
    control=Control()
    if not control.allowed():
        print(json.dumps({'status':'paused'}));return
    control.reconcile()
    print(json.dumps({'routes':[dispatch(control,r) for r in manifest()['routes']
        if r['execution_enabled'] and r['route_kind']!='migration_probe']}))

if __name__=='__main__':main()
