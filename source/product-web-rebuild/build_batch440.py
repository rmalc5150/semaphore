from research_helpers import *
a=ev('https://www.jafco.co.jp/english/introduction/','Issuer describes private equity investment business, venture and buyout pillars.')
b=ev('https://www.jafco.co.jp/english/ir/overview/','Issuer business model is fund management and investment returns.')
c=ev('https://www.jafco.co.jp/english/venture_investment/','Portfolio-company products distinguished from investor own products.')
co=dict(company_id='cmp_355c0b6c-8e58-4888-8555-a3c3dada90e0',products=[],evidence=[a,b,c],status='complete',coverage_note='No directly attributable products in biotech, robotics, semiconductors or energy storage identified in reviewed current business model and venture portfolio materials. JAFCO provides fund management/investment services; portfolio equity ownership alone does not establish a product developer/manufacturer/licensee/commercial-partner relationship. Financial funds and investee products excluded. Completion refers to this scoped public-web scan, not a guarantee against future new qualifying activities.')
(out/'batch-0440.json').write_text(json.dumps({'companies':[co]},indent=2))
