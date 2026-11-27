import json
from pathlib import Path
from public_statistics_apis import PORTWATCH,UNIDO
P=Path(__file__).parent
sources=[{'source_id':'C069','source':'imf_portwatch_shipping_activity','adapter':'additional_portwatch','api':PORTWATCH,'enabled':True,'historical':True,'coverage_note':'Native provider port/day attributes from 2019; estimated shipping activity, current revisions, seven-day publication lag; no pre-2019 history or customs shipment claim.'},{'source_id':'C067','source':'unido_iip_and_indstat','adapter':'additional_unido','api':UNIDO+'getData','enabled':True,'historical':True,'coverage_note':'Native IIP and INDSTAT4 current measurements by dynamically discovered country, variable, activity and period; annual scopes since 2016, daily revisits last two years; catalogue pages are not measurements.'}]
(P/'statistics-sources.json').write_text(json.dumps(sources,indent=2)+'\n')
