# Give the EC2 collector access to BigQuery

Project shown in the user's console: `patent-research-508613`.
Verified EC2 role: `arn:aws:iam::059416028963:role/lambdaEc2ForEc2Instance`.

Use Workload Identity Federation so this AWS role can obtain temporary Google
credentials. There is no service-account private key to download or rotate.
The setup creates `optima-patent-collector@patent-research-508613.iam.gserviceaccount.com`
with BigQuery Job User in the project. Access to the public patent dataset comes
from the dataset's public permissions. This does not grant access to private
datasets; grant dataset-scoped Data Viewer only if private inputs are needed.

1. In Google Cloud Console, select `patent-research-508613` and confirm billing
   is enabled. Click the Cloud Shell terminal icon (`>_`) at the upper right.
2. Open `config/setup-google-patents-access.sh`, copy its complete contents into
   a Cloud Shell file named `setup-google-patents-access.sh`, and run:
   `bash setup-google-patents-access.sh`.
   Alternatively, paste its commands directly into Cloud Shell.
3. Authorize Cloud Shell if Google prompts. Use an account that can enable APIs,
   create service accounts and workload identity pools, and grant project IAM
   roles. The script stops on an error; report the error before rerunning a
   partially completed setup.
4. Send back the project number printed after `Setup completed`. No password,
   API key, access token or private key is needed. The collector can construct
   the nonsecret federation configuration from that number and the fixed names
   in the setup script. The generated `optima-patents-aws.json` is also a
   nonsecret configuration file if you prefer to copy it to EC2.

Next on EC2: configure Google Application Default Credentials to use the
federation configuration, test authentication and public table metadata, then
dry-run the prepared query and inspect estimated scan size. A successful
connection does not by itself start an unrestricted backfill. Enforce an
explicit `maximumBytesBilled` on each executed query, retain export provenance,
and save JSONL into the prepared S3 inbox.

Connection verified on September 22, 2026. The user completed Google setup and
supplied project number `24037405713`. EC2 successfully authenticated through
the federation configuration in `config/google-patents-aws.json`, read the public
table metadata, and dry-ran the generated January 2025 query. No service-account
private key is stored. Install dependencies with `requirements-patents.txt`.

The patent commands load that credential file explicitly, so no global shell
configuration or credentials for other collectors are changed. For another
Google client using Application Default Credentials, set
`GOOGLE_APPLICATION_CREDENTIALS` to this file's absolute path and specify project
`patent-research-508613`.

Repeat the metadata and dry-run check with:

```bash
.venv-athena/bin/python patent_bigquery_access.py
```

The check cannot execute a billed data query. It records the planned execution
ceiling separately from the scan estimate, including when the estimate exceeds
the ceiling. Results are in `reports/patent-bigquery-access.json`.

At the September 22 check, the table in US had 170,418,479 rows and reported a last modification on
April 26, 2026. A separate bounded aggregate verified latest publication dates:
CN April 10, EP April 15, JP April 10, KR March 31, US April 21, WO April 9, 2026.
These maxima do not establish complete coverage up to those dates. The source
was useful for historical discovery but did not support daily global
patent freshness. Details are in `reports/patent-bigquery-freshness.json`.

The source changed September 23. A new full-authority audit now verifies
173,516,400 rows, with latest CN publication September 8 and US September 17.
The current-universe extraction estimate is 47,135,127,425 bytes, still within
50 GB. See [PATENT_BACKFILL_PLAN.md](PATENT_BACKFILL_PLAN.md) for current coverage,
costs, source gaps and unexecuted backfill options. Earlier figures below describe
the September 22 pilot.

The January query estimate is 46,117,420,778 bytes (0.04194 TiB), approximately
$0.26 at the published US on-demand rate of $6.25/TiB before free usage/credits.
The original generated plan's 1 GB placeholder ceiling is insufficient. The
bounded historical command uses an explicit 50 GB ceiling (about $0.28), which
is enforced by BigQuery. This is a query-analysis ceiling, not a total cap on
S3 storage, API requests, or other platform charges.

References:
- https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-other-clouds
- https://docs.cloud.google.com/sdk/gcloud/reference/iam/workload-identity-pools/create-cred-config
- https://docs.cloud.google.com/bigquery/docs/access-control#bigquery.jobUser
