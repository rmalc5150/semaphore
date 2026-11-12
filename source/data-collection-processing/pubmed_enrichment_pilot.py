"""Reproduce S27 sample extraction and export reviewed takeaways without catalog writes."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from pubmed_enrichment import enrich


def run(sample, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    reviews=json.loads((output/'reviewed-takeaways.json').read_text())
    with open(sample,newline='') as handle:
        rows=list(csv.DictReader(handle,delimiter='\t'))
    result=[]
    for row in rows:
        payload=json.loads(row['payload_json'])
        data=payload['data']
        facts=enrich(data['article_xml'],data['pmid'])
        result.append({'provider_id':row['provider_id'],'pmid':facts['pmid'],'source_url':row['source_url'],
            'parent_observation_id':row['observation_id'],'enrichment':facts,
            'reviewed_interpretation':reviews['reviews'][facts['pmid']],
            'review_scope':reviews['review_method']})
        if facts['pmid']=='34655480' and (output/'fulltext-probe.json').exists():
            probe=json.loads((output/'fulltext-probe.json').read_text())
            result[-1]['additional_fulltext_evidence']=probe['evidence']
            result[-1]['additional_fulltext_status']='Retrieved through official Europe PMC API and reviewed for this pilot; original PubMed record has no abstract.'
    summary={'sample_records':len(result),'distinct_pmids':len({r['pmid'] for r in result}),
        'abstracts_present':sum(bool(r['enrichment']['abstract_sections']) for r in result),
        'explicit_author_conclusions':sum(bool(r['enrichment']['key_takeaway']) for r in result),
        'study_designs':dict(Counter(r['enrichment']['study_design'] for r in result)),
        'papers_with_declared_trial_registration':sum(any(any(e['role']=='declared_registration' for e in t['evidence']) for t in r['enrichment']['trial_links']) for r in result),
        'indexing_design_conflicts':sum(any(f['code']=='indexing_design_conflict' for f in r['enrichment']['quality_flags']) for r in result),
        'reviewed_takeaways':len(result),'missing_abstract_full_text_reviewed_in_pilot':['34655480'],
        'input_sha256':hashlib.sha256(Path(sample).read_bytes()).hexdigest(),
        'scope':'Sample pilot and future-collection enrichment. No S27 archive backfill, catalog writes, completion email or company/product/person ID promotion.'}
    for name,data in [('sample-enrichment.json',result),('summary.json',summary)]:
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    with (output/'sample-review.csv').open('w',newline='') as handle:
        fields=['pmid','title','design','signal','takeaway','limitation','evidence_basis','publication_date','declared_trial_ids','quality_flags']
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for r in result:
            facts=r['enrichment'];review=r['reviewed_interpretation'];pub=facts['publication_event']['date']
            writer.writerow({'pmid':r['pmid'],'title':facts['title'],**{k:review[k] for k in ('design','signal','takeaway','limitation')},
                'evidence_basis':review['basis'],'publication_date':pub['value'] if pub else '',
                'declared_trial_ids':' | '.join(t['trial_id'] for t in facts['trial_links'] if any(e['role']=='declared_registration' for e in t['evidence'])),
                'quality_flags':' | '.join(f['code'] for f in facts['quality_flags'])})
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample',required=True)
    parser.add_argument('--output',default='reports/pubmed-enrichment-pilot-2026-10-16')
    args=parser.parse_args();run(args.sample,args.output)
