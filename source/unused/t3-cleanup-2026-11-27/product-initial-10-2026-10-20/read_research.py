import json,boto3
s=boto3.Session(region_name='us-east-1')
x=json.loads(s.client('s3').get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/source_documents/product_catalogue/078513afce59b4fb7d4bcc2791d7d105ddbd257105173f5a6c0da08dc501e644')['Body'].read())
for item in x['output']:
 for content in item.get('content',[]):
  if content.get('type')=='output_text':print(content['text'])
