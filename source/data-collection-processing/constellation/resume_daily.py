"""Resume existing daily capture/publication schedules; preserve source pauses and c7i routing."""
import json
from datetime import datetime,timezone
from pathlib import Path
import subprocess
from source_pauses import unit_pause

ROOT=Path(__file__).resolve().parents[1]
DAILY_NAMES='''authenticated-daily caiso-daily chictr-daily collection-daily committed-athena company-catalogue conference-collection conference-publication doe-storage-daily edinet-documents-daily eodhd-inventory eodhd-profiles federal-register-daily-enrichment grant-daily market-collection market-publication news-collection news-publication nist-robotics-daily nist-robotics-matching patents-daily patents-global-monitor patents-prosecution patents-prosecution-publication people-collection product-search-daily research-publication search-capture source-schedule-daily specialist-daily specialist-publication trade-screening-enrichment'''.split()

def main():
    before=json.loads((ROOT/'constellation/status/daily-timers-before.json').read_text())
    indexed={r['unit']:r for r in before};selected=[]
    for name in DAILY_NAMES:
        unit='optima-'+name+'.service';r=indexed[unit];command=r['command']
        if unit_pause(unit):raise RuntimeError('Refusing owner-paused source: '+unit)
        if 'constellation.legacy_dispatch' in command or 'collect_historical.py' in command or '--mode historical' in command or '--lane historical' in command:
            raise RuntimeError('Historical payload in daily selection: '+unit)
        selected.append(r)
    # New historical work stays with the dedicated c7i dispatch timer.
    subprocess.run(['systemctl','enable','--now',*[r['timer'] for r in selected]],check=True)
    config=ROOT/'config/collection-monitoring.json';data=json.loads(config.read_text())
    for row in selected:
        data['jobs'].get(row['unit'],{}).pop('maintenance_pause_reason',None)
    config.write_text(json.dumps(data,indent=2)+'\n')
    result={'resumed_at':datetime.now(timezone.utc).isoformat(),'host':'i-070bab0b09f794629','resumed_timers':[],
        'source_specific_pauses_preserved':True,'historical_payloads_on_controller':False}
    for row in selected:
        enabled=subprocess.check_output(['systemctl','is-enabled',row['timer']],text=True).strip()
        active=subprocess.check_output(['systemctl','is-active',row['timer']],text=True).strip()
        assert enabled=='enabled' and active=='active'
        result['resumed_timers'].append({'unit':row['unit'],'timer':row['timer'],'enabled':enabled,'state':active})
    (ROOT/'constellation/status/daily-resume.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'resumed_timers':len(selected),'source_specific_pauses_preserved':True}))

if __name__=='__main__':main()
