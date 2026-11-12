ARN: arn:aws:secretsmanager:us-east-1:059416028963:secret:dataSourceAPIkeys-PSTzff



comtrade (51):
UN-primary
UN-secondary

fred_alfred (66):
FRED

ember (70): 
Ember

wto (71, 72, 73):
WTO-primary
WTO-secondary

epo_ops (74): 
EPO-consumer
EPO-consumer-secret
Validated 2026-10-26 20:51 CET: OAuth and legal-data endpoint HTTP 200. Historical and daily collection active; first captures verified in S3.

copernicus (75): 
copernicus

November 4: owner accepted terms. ERA5 single-levels and ERA5-Land API sample retrieval jobs both completed successfully. No further licence-acceptance action needed. Production capture, structured extraction and Athena publication remain engineering verification.

ucdp (78): 
**emailed

nice (88): 
NICE replied: syndication application and cybersecurity certification/report review required. API key pending approval/licence. Final guidance only; development documents excluded. Public collection paused.

opendart (98):
dart

kosis (99):
**emailed

census (118):
US-census

November 4, 12:51 UTC: after email activation, the stored US-census key passed the February 2016 trade query (36 rows). No replacement key needed. Production resumption and Athena publication remain to be verified.

usda_fas (125):
usda-fas

November 7: current host api.fas.usda.gov with api_key query authentication verified using the existing usda-fas key; 1,875 unique 2016 PSD records returned. Old OpenData host/header route caused the failure. Production Athena publication remains to verify.

meta_ads (131): 
**asked Jason to use his account

tiktok_ads (132):
TikTok-client
TikTok-secret
TikTok-ID
Validated 2026-10-27 10:09 CET: client OAuth HTTP 200 and access token issued. Commercial Content ad queries returned HTTP 500/internal_error twice, including a minimal request. Product access is not yet verified; daily and historical capture have not started. Documented ad-query date range starts within the past year, so 2016 backfill is unavailable through this endpoint. Evidence: data-collection-processing/constellation/tiktok/access-validation.json and access-retry.json. No credential or token values were saved.

The TikTok keys passed authentication, but the Commercial Content API returned HTTP 500 twice. Daily and historical capture have therefore not started.

I recorded the results in [apiKeyRegister.md](/home/ec2-user/apiKeyRegister.md).

Also, this endpoint only supports ad queries within the past year, so it cannot provide history back to 2016. TikTok documentation.

linkedin_ads (133):
**filled out the form

x_ads (134):
X-client
X-secret
X-bearer
Tested 2026-10-27 10:47 CET using the stored X-bearer field. Public user lookup: HTTP 402, credits depleted. Ads Repository export: HTTP 403, code 453, current access level excludes the endpoint. No records collected; daily/historical capture remains inactive. Ordinary API reads require credits; Ads Repository access needs the appropriate product entitlement separately. Evidence: data-collection-processing/constellation/x/access-validation.json. No credential/token values were saved.
