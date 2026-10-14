#!/usr/bin/env python3
"""Create conservative, observation-pinned review decisions for an EODHD release."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import pyarrow.parquet as pq

from research_contract import ROOT, load_json


SECTORS={"biotech","robotics","semiconductors","energy_storage"}


def _has(text,patterns):
    return any(re.search(pattern,text,re.I|re.S) for pattern in patterns)


def classify(sector,profile):
    description=(profile.get('description') or '').strip()
    labels=' '.join(str(profile.get(k) or '') for k in ('sector','industry','gics_industry','gics_subindustry'))
    text=description+' '+labels
    if not description or 'no profile data available' in description.lower():
        return 'needs_more_evidence','The provider returned no substantive business description; labels alone are insufficient.'
    if sector=='biotech':
        positive=[r'\b(?:develops?|discovers?|manufactures?|commerciali[sz]es?|provides?|offers?)\b.{0,180}\b(?:drugs?|medicines?|vaccines?|antibod(?:y|ies)|gene therap\w*|cell therap\w*|molecular diagnostic\w*|genomic\w*|biologic\w*)\b',
                  r'\b(?:biotech(?:nology)?|biopharmaceutical) compan(?:y|ies)\b']
        if _has(description,positive):return 'supported','The business description explicitly identifies biotechnology products or development activity.'
    elif sector=='robotics':
        if _has(description,[r'robotic process automation']) and not _has(description,[r'\b(?:robot|robotic system|cobot|autonomous vehicle|autonomous mobile robot)\w*\b']):
            return 'rejected','The match describes business-process automation software rather than physical robotics or autonomy.'
        positive=[r'\b(?:develops?|designs?|manufactures?|produces?|provides?|offers?)\b.{0,180}\b(?:robots?|robotic systems?|cobots?|autonomous vehicles?|autonomous mobile robots?|machine vision)\b',
                  r'\b(?:robots?|robotic systems?|cobots?)\b.{0,180}\b(?:develops?|designs?|manufactures?|products?|systems?)\b']
        if _has(description,positive):return 'supported','The business description explicitly identifies robotics, autonomy, or enabling systems as an activity.'
    elif sector=='semiconductors':
        if _has(profile.get('name') or '',[r'\bwarrant\b',r'\bREIT\b',r'\bbank\b']):
            return 'needs_more_evidence','The security name conflicts with the semiconductor label; issuer and instrument need corroboration.'
        positive=[r'\b(?:designs?|develops?|manufactures?|fabricates?|produces?|supplies?|provides?)\b.{0,180}\b(?:semiconductors?|integrated circuits?|microchips?|chips?|semiconductor wafers?|lithograph\w*|microprocessors?)\b',
                  r'\b(?:semiconductors?|integrated circuits?|semiconductor wafers?)\b.{0,180}\b(?:design|manufactur|fabricat|equipment|materials|packag)\w*']
        if _has(description,positive):return 'supported','The business description explicitly identifies semiconductor design, production, materials, packaging, or equipment.'
    else:
        if _has(description,[r'\b(?:mining|mineral (?:exploration|deposits?)|ore deposits?)\b']) and not _has(description,[r'\b(?:battery|energy storage) (?:systems?|products?|technology|assets?|solutions?)\b']):
            return 'rejected','The description concerns raw-material extraction without an established storage-technology activity.'
        battery=r'(?:batteries|(?:lithium[- ]ion|solid[- ]state|lead[- ]acid|flow) batter(?:y|ies)|battery (?:cells?|packs?|systems?|technology|materials?|products?|solutions?|storage))'
        positive=[rf'\b(?:develops?|designs?|manufactures?|produces?|provides?|offers?|operates?|owns?|distributes?|trades?)\b.{{0,180}}\b(?:{battery}|supercapacitor\w*|ultracapacitor\w*|energy storage systems?|thermal storage|heat storage|molten salt storage|pumped hydro\w*|flywheel storage|compressed air energy storage|hydrogen storage|hydrogen tanks?)\b',
                  rf'\b(?:{battery}|supercapacitor\w*|energy storage systems?|hydrogen storage)\b.{{0,180}}\b(?:technology|products?|systems?|solutions?|manufactur|develop|operat|distribut)\w*']
        if _has(description,positive):return 'supported','The business description explicitly identifies an agreed energy-storage technology, product, system, or operated asset.'
    if _has(labels,[re.escape(sector.replace('_',' ')),r'biotechnolog',r'semiconductor']):
        return 'needs_more_evidence','A provider classification suggests the sector, but the business description does not establish the agreed activity.'
    return 'needs_more_evidence','The textual match is contextual or too weak to establish a sector membership without another source.'


def decisions(parent_dir,previous=None):
    parent_dir=Path(parent_dir);release=load_json(parent_dir/'release.json')
    profiles={r['provider_symbol']:r for r in pq.read_table(parent_dir/release['files']['company_profiles']['path']).to_pylist()}
    candidates=pq.read_table(parent_dir/release['files']['sector_candidates']['path']).to_pylist()
    old={};old_company=[]
    if previous:
        value=load_json(Path(previous))
        for row in value.get('sector_decisions',[]):old[(row['provider_symbol'],row['sector_id'],row['profile_observation_id'])]=row
        old_company=value.get('company_decisions',[])
    result=[]
    for candidate in candidates:
        symbol=candidate['provider_symbol'];sector=candidate['sector_id'];profile=profiles[symbol]
        key=(symbol,sector,profile['observation_id'])
        if key in old:
            result.append({**old[key]})
            continue
        status,reason=classify(sector,profile)
        result.append({'provider_symbol':symbol,'sector_id':sector,'profile_observation_id':profile['observation_id'],
            'review_status':status,'reason':reason,'review_basis':'conservative_rule_assisted_profile_review',
            'evidence_urls':[profile['source_url']]})
    # Preserve prior reviewed false negatives while their exact observations remain current.
    candidate_keys={(r['provider_symbol'],r['sector_id']) for r in result}
    for row in old.values():
        key=(row['provider_symbol'],row['sector_id'])
        if key not in candidate_keys and row['provider_symbol'] in profiles and row['profile_observation_id']==profiles[row['provider_symbol']]['observation_id']:
            result.append({**row});candidate_keys.add(key)
    company=[]
    for row in old_company:
        profile=profiles.get(row['provider_symbol'])
        if profile and row['profile_observation_id']==profile['observation_id']:company.append(row)
    return {'parent_release_id':release['release_id'],'reviewed_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'method':'Prior manual decisions are preserved. New candidates receive conservative rule-assisted review; needs_more_evidence is not a rejection.',
        'sector_decisions':sorted(result,key=lambda r:(r['provider_symbol'],r['sector_id'])),
        'company_decisions':company}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent-dir',type=Path,required=True)
    p.add_argument('--previous',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    value=decisions(a.parent_dir,a.previous);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(value,indent=2)+'\n')
    counts={}
    for row in value['sector_decisions']:
        key=(row['sector_id'],row['review_status']);counts[key]=counts.get(key,0)+1
    print(json.dumps({'decisions':len(value['sector_decisions']),'counts':[(*k,v) for k,v in sorted(counts.items())]}))


if __name__=='__main__':main()
