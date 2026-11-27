"""Record only the verification this review has actually obtained."""
import json
import os
from pathlib import Path
import re
from stat import S_IMODE

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
NOTES={
 106:'The old crawler requested the API homepage. The replacement uses the official Comex Stat POST query for four battery and mineral NCM products, with native monthly import and export FOB values and kilograms.',
 107:'The old crawler started at the homepage. The replacement targets the official COCHILCO statistical workbook for 2000–2025 and earlier annual releases.',
 108:'The old yearbook URL was outdated, and the current host omits its certificate intermediate. The replacement targets the official archive and uses an independently verified intermediate with hostname verification.',
 109:'SNIFA’s portal now links directly to the official sanctioning-proceedings export. This covers proceedings. Inspections, final sanctions and regulated-unit records remain separate.',
 110:'The general ministry crawler followed unrelated publication indexes. The replacement follows the official bulletin and yearbook archives and their original spreadsheets and PDFs.',
 111:'The dashboard crawler did not reach the native data. The replacement targets official SIACAM production index, change and lithium CSV exports.',
 112:'The old map viewer exposed a discovery page. The replacement targets the current SIGMINE state shapefiles and Cadastro Mineiro CSVs and verifies archive structure and record counts. Older snapshots still need a provider archive.',
 113:'The map homepage supplied no features. The official GEOCATMIN query now returns eight Tacna concession features with original attributes and geometry. The wider cadastre and dated snapshots remain open.',
 114:'The owner deferred the paid API. If resumed, shipment and supplier collection requires ImportYeti API access and data credits.',
 115:'The owner deferred the paid API. If resumed, collection requires an ImportGenius API agreement covering the intended countries and historical periods.',
 116:'No API credentials or capture route are configured. MarineTraffic needs provisioned historical vessel track and port call access for the intended vessels or ports.',
 117:'The owner deferred the paid API. If resumed, collection requires Kpler commodity cargo flow access and API credentials.',
 118:'The collectors saved real Census responses, but the generic metadata validator rejected the tabular JSON. The repaired validator matches each exact native row, checks the repeated predicate columns and preserves reported zeros and query scope. During this review, a separate daily API request timed out and was scheduled to retry on 21 November at 06:45 Madrid time. Historical periods the Census API has yet to release remain open.',
 119:'The previous SQL sample came from a methodology PDF. The replacement uses the official Comext endpoint and preserves native euro values and any returned flags. The initial scope is Germany–US trade for four HS6 products.',
 120:'The download page was treated as input data. The replacement uses annual native emissions and activity records for five selected iron and steel assets. Broader industrial coverage remains open.',
}
PARTIAL={109,112,113,119,120}
DEFERRED={114,115,117}
COMMERCIAL={
 114:'https://www.importyeti.com/yeti-api',
 115:'https://www.importgenius.com/pricing',
 116:'https://servicedocs-sm.kpler.com/',
 117:'https://help.kpler.com/en/articles/6022217-kpler-api-and-sdk-introduction',
}


def replace_document(path,text):
    original=path.stat()
    temporary=path.with_name(path.name+'.source-review')
    temporary.write_text(text)
    temporary.chmod(S_IMODE(original.st_mode))
    if os.geteuid()==0:
        os.chown(temporary,original.st_uid,original.st_gid)
    temporary.replace(path)


def write(live=None):
    live=live or {}
    entries=json.loads((P/'entries.json').read_text())
    staged=json.loads((P/'staged-raw-proof.json').read_text())
    census=json.loads((P/'census-proof.json').read_text())
    audit=json.loads((P/'before.json').read_text())
    result={}
    for entry in entries:
        number=entry['entry']
        source=entry['source']
        verified=live.get('sources',{}).get(source,{})
        blocked=number in COMMERCIAL
        passed=verified.get('verified',False)
        failed=live.get('raw_proof_failures',{}).get(source)
        samples=verified.get('athena_samples',[])
        raw=[]
        for sample in samples:
            raw.append(sample['provider_original'])
        if not raw:
            raw=[row['artifact']['s3_uri'] for batch in staged.get(source,{}).values()
                 for row in batch if row['state']=='validated_raw']
        if number==118 and not raw:
            raw=[row['artifact']['s3_uri'] for row in census if row['status']=='verified']
        raw=list(dict.fromkeys(raw))
        if number in DEFERRED:
            status='deferred by owner'
        elif blocked:
            status='blocked by provider access'
        elif passed and number in PARTIAL:
            status='partial — verified scope only'
        elif passed and any(mode.get('failures') for mode in verified['capture'].values()):
            status='partial — capture errors remain'
        elif passed:
            status='reviewed'
        elif failed:
            status='raw proof incomplete'
        elif live:
            status='production verification incomplete'
        else:
            status='awaiting m7 deployment and Athena verification'
        result[source]={**entry,'status':status,'reviewed':status=='reviewed',
                        'findings':NOTES[number],'raw_originals':raw[:4],
                        'live':verified,'worker_raw_failure':failed,
                        'previous_metadata_state':audit[source]['source']['state'],
                        'provider_access_reference':COMMERCIAL.get(number)}
    summary={'entries':result,'athena_query_id':live.get('athena_query_id'),
             'census_validated_daily_rows':sum(r['rows'] for r in census if r.get('mode')=='daily' and r['status']=='verified'),
             'census_validated_historical_rows':sum(r['rows'] for r in census if r.get('mode')=='historical' and r['status']=='verified'),
             'stage_evidence':'staged-raw-proof.json','live_evidence':'live-verification.json' if live else None,
             'deployment_monitor':'deployment-state.json'}
    (P/'review-status.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')

    checklist=ROOT/'RAW_DATA_VERIFICATION_SCHEDULE.md'
    text=checklist.read_text()
    backup=P/'checklist-before.md'
    if not backup.exists():
        backup.write_text(text)
    for entry in reversed(entries):
        number=entry['entry']
        source=entry['source']
        row=result[source]
        pattern=rf'^- \[[ x]\] \*\*{number}\. .*?(?=^- \[[ x]\] \*\*\d+\.|^### Day |\Z)'
        match=re.search(pattern,text,re.M|re.S)
        assert match,number
        block=re.sub(r'\n  Review \(20 November 2026\):[^\n]*','',match.group())
        block=re.sub(r'^- \[[ x]\]', '- [x]' if row['reviewed'] else '- [ ]',block,count=1)
        if row['raw_originals']:
            prefix=row['raw_originals'][0].rsplit('/',1)[0]+'/'
            block=re.sub(r'^  Raw S3:.*$',f'  Raw S3: `{prefix}` (original provider objects).  ',block,flags=re.M)
        if number in DEFERRED:
            block=re.sub(r'^  Current collection state:.*$','  Current collection state: **deferred by owner. No capture route configured.**  ',block,flags=re.M)
        elif number in COMMERCIAL:
            block=re.sub(r'^  Current collection state:.*$','  Current collection state: **blocked by provider access. No capture route configured.**  ',block,flags=re.M)
        elif row['live'].get('verified'):
            block=re.sub(r'^  Current collection state:.*$','  Current collection state: **enabled. Daily capture, historical capture and metadata publication verified for the scope below.**  ',block,flags=re.M)
        else:
            control=row['live'].get('metadata_control') or audit[source]['source']
            current=f'  Current collection state: Metadata source **{control["state"]}**'
            if control.get('last_reason'):
                current+=f'. Latest reason `{control["last_reason"]}`'
            current+='.  '
            block=re.sub(r'^  Current collection state:.*$',lambda _match:current,block,flags=re.M)
        if row['live'].get('athena_samples'):
            ids=','.join(repr(v['job_id']) for v in row['live']['athena_samples'])
            sql="SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = '"+source+"' AND contract_version = '2.0.3' AND job_id IN ("+ids+") GROUP BY source_key, dataset;"
            block=re.sub(r'^  Athena SQL:.*$',f'  Athena SQL: `{sql}`',block,flags=re.M)
        sentence=f'  Review (20 November 2026): **{row["status"]}**. {row["findings"]}'
        if row['raw_originals']:
            sentence+=f' Verified raw example: `{row["raw_originals"][0]}`.'
        if row['provider_access_reference']:
            sentence+=f' [Provider access]({row["provider_access_reference"]}).'
        failure=row['worker_raw_failure']
        if failure:
            errors=list(dict.fromkeys(item['error'] for item in failure.get('errors',[])))
            missing=[mode for mode in ('daily','historical') if not failure.get(mode)]
            if missing:
                sentence+=f' No verified native input in {" and ".join(missing)} capture.'
            elif not errors:
                sentence+=' Daily and historical inputs did not prove distinct editions.'
            if errors:
                sentence+=' Worker findings: '+', '.join(' '.join(error.split()) for error in errors[:2])+'.'
        for mode,capture in row['live'].get('capture',{}).items():
            failures=capture.get('failures',{})
            if failures:
                reasons=sorted({entry['reason'] for entry in failures.values()})
                sentence+=f' {mode.capitalize()} capture has {len(failures)} unresolved URL failures ({", ".join(reasons[:3])}).'
        sentence+=' [Review evidence](repair-notes/2026-11-20-entries-106-120/review-status.json).'
        text=text[:match.start()]+block.rstrip()+'\n\n'+sentence+'\n\n'+text[match.end():]
    replace_document(checklist,text)

    if live:
        status_doc=ROOT.parent/'data-source-status-2026-10-26.md'
        body=status_doc.read_text()
        for entry in entries:
            number=entry['entry']
            row=result[entry['source']]
            if not row['live'].get('athena_samples'):
                continue
            title=f'### q{number:03d}'
            marker=re.search(rf'^{re.escape(title)}\n.*?(?=^### |^## |\Z)',body,re.M|re.S)
            ids=', '.join(repr(m['job_id']) for m in row['live']['athena_samples'])
            query=(f"SELECT source_key, dataset, count(*) AS observations, "
                   f"min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original "
                   f"FROM optima_metadata_engine.source_observations WHERE source_key = '{entry['source']}' "
                   f"AND contract_version = '2.0.3' AND job_id IN ({ids}) GROUP BY source_key, dataset;")
            section=f'{title}\n\n**{number:03d}. {entry["name"]}**\n\nVerified published sample. Workgroup `optima-collected-data`.\n\n```sql\n{query}\n```\n\n'
            if marker:
                body=body[:marker.start()]+section+body[marker.end():]
            else:
                following=re.search(rf'^### q{number+1:03d}\n',body,re.M)
                if following:
                    body=body[:following.start()]+section+body[following.start():]
        replace_document(status_doc,body)


if __name__=='__main__':
    write()
