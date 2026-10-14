# IBKR HKEX news collector

This collector resolves a numeric HKEX stock through IBKR, downloads historical
news headlines and entitled article bodies, and writes one JSON document to the
processed S3 prefix.

## 1. Prepare Interactive Brokers

1. Use a fully opened IBKR account and install the current **offline TWS** or
   **IB Gateway**, plus the matching TWS API package. Current IBKR Python API
   releases require Python 3.11 or newer.
2. In Client Portal, check **Settings > Market Data Subscriptions > News and
   Research**. Subscribe to the news services needed for the HKEX instrument.
   `reqNewsProviders` only returns providers to which the logged-in user is
   entitled; some articles may require paid subscriptions.
3. In TWS open **Edit > Global Configuration > API > Settings** (in Gateway,
   **Configure > Settings > API > Settings**):
   - enable socket clients;
   - keep read-only API enabled, because this job never trades;
   - set the socket port (paper TWS normally `7497`, live TWS `7496`; Gateway
     normally `4002` paper and `4001` live—use the value shown in your app);
   - add the collector host to trusted IPs if it is not on the same machine.
4. Log in to TWS/Gateway and complete 2FA before running the collector. Do not
   store an IBKR username, password, or 2FA seed in AWS. The socket API has no
   API key: the running TWS/Gateway session supplies authentication.
5. Install the official Python client from the downloaded API bundle:

       cd TWS_API/source/pythonclient
       python3 -m pip install .

TWS/Gateway must be running and reachable from the job. For AWS, run Gateway on
a persistent private host; do not expose its API port publicly. IBKR sessions
need periodic reauthentication, so a plain unattended Lambda is not sufficient.

## 2. Create the AWS secret

The secret contains connection/configuration values, not IBKR credentials. Let
the EC2/ECS/Lambda role provide AWS credentials; never put AWS access keys here.

Create `ibkr-news-secret.json` locally:

```json
{
  "ib_host": "127.0.0.1",
  "ib_port": 7497,
  "client_id": 91,
  "news_provider_codes": ["BRFG", "DJNL"],
  "s3_bucket": "YOUR-DATA-BUCKET",
  "s3_processed_prefix": "processed/ibkr-news",
  "s3_encryption": "AES256"
}
```

Provider codes vary by account. Omit `news_provider_codes` on the first run to
use all entitled providers, then retain only the desired codes. Create/update the
secret without committing the JSON file:

```bash
aws secretsmanager create-secret \
  --name prod/data-collection/ibkr-news \
  --secret-string file://ibkr-news-secret.json

aws secretsmanager put-secret-value \
  --secret-id prod/data-collection/ibkr-news \
  --secret-string file://ibkr-news-secret.json
```

The job's IAM role needs `secretsmanager:GetSecretValue` on that secret,
`s3:PutObject` on `arn:aws:s3:::YOUR-DATA-BUCKET/processed/ibkr-news/*`, and
`kms:Encrypt` if `s3_encryption` is changed to `aws:kms` (also add the KMS key ID
to the script/config before using KMS).

## 3. Run

```bash
python3 -m pip install -r requirements.txt
python3 ibkr_hkex_news.py 00700 --days 7 --limit 50 \
  --secret-id prod/data-collection/ibkr-news --region ap-east-1
```

Output lands at:

```text
s3://YOUR-DATA-BUCKET/processed/ibkr-news/exchange=HKEX/symbol=00700/YYYY/MM/DD/<timestamp>.json
```

Use a distinct `client_id` for every simultaneous API program. First test with
the paper account/port. An empty result can be legitimate, but errors about
permissions usually mean the selected news provider is not subscribed.
