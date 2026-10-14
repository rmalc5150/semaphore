"""Publish only the reviewed SMS legal pages in a dedicated public bucket."""
import json
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
BUCKET='optima-collection-sms-public-059416028963-us-east-1'
s3=boto3.client('s3',region_name='us-east-1')
try:
 s3.create_bucket(Bucket=BUCKET,ObjectOwnership='BucketOwnerEnforced')
except ClientError as e:
 if e.response['Error']['Code']!='BucketAlreadyOwnedByYou': raise
s3.put_bucket_tagging(Bucket=BUCKET,Tagging={'TagSet':[{'Key':'Project','Value':'OptimaCollectionMonitoring'},{'Key':'Purpose','Value':'Public SMS legal pages only'}]})
s3.put_bucket_encryption(Bucket=BUCKET,ServerSideEncryptionConfiguration={'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]})
s3.put_public_access_block(Bucket=BUCKET,PublicAccessBlockConfiguration={'BlockPublicAcls':True,'IgnorePublicAcls':True,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
keys=['sms-terms.html','sms-privacy.html']
s3.put_bucket_policy(Bucket=BUCKET,Policy=json.dumps({'Version':'2012-10-17','Statement':[{'Sid':'ReadPublishedLegalPages','Effect':'Allow','Principal':'*','Action':'s3:GetObject','Resource':[f'arn:aws:s3:::{BUCKET}/{key}' for key in keys]}]}))
for key in keys:
 s3.put_object(Bucket=BUCKET,Key=key,Body=Path('reports',key).read_bytes(),ContentType='text/html; charset=utf-8',CacheControl='public, max-age=300')
 print(f'https://{BUCKET}.s3.us-east-1.amazonaws.com/{key}')
