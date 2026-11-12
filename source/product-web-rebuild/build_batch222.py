from research_helpers import *
receipt=json.loads((out/'batch-0212.receipt.json').read_text())
co=receipt['manifest']['companies'][0]
for item in co['products']:
 item['product_id']=item.pop('inserted_product_id')
co['company_id']='cmp_09538592-f628-407b-9142-4f7379aaf839'
co['coverage_note']='Shared product identities from batch 212 linked to second SmartKem listing entry. Live company descriptions both identify Manchester-founded 2009 TRUFLEX materials issuer, and provider symbols are SMTK/SMTKD. Existing company auto-review evidence has conflicting CIKs (0817516 versus 1817760); company records not merged or identity fields changed. Partial: resolve upstream CIK inconsistency, auxiliary material codes and further current product portfolio. No duplicate products created.'
(out/'batch-0222.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(co['products']))
