#!/usr/bin/env bash
# Run in GOOGLE CLOUD SHELL as a project administrator, not on EC2.
# Creates federation for the existing EC2 role. No private key is created.
# Stop on any failure; send the error before retrying an incomplete setup.
set -euo pipefail

PATENT_PROJECT='patent-research-508613'
PATENT_ACCOUNT='optima-patent-collector'
PATENT_POOL='optima-patents-aws'
PATENT_PROVIDER='optima-ec2'
PATENT_AWS_ACCOUNT='059416028963'
PATENT_AWS_ROLE='lambdaEc2ForEc2Instance'
PATENT_SERVICE_ACCOUNT="${PATENT_ACCOUNT}@${PATENT_PROJECT}.iam.gserviceaccount.com"

gcloud services enable \
  bigquery.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  --project="$PATENT_PROJECT"

PATENT_PROJECT_NUMBER="$(gcloud projects describe "$PATENT_PROJECT" --format='value(projectNumber)')"
[[ "$PATENT_PROJECT_NUMBER" =~ ^[0-9]+$ ]]

gcloud iam service-accounts create "$PATENT_ACCOUNT" \
  --project="$PATENT_PROJECT" \
  --display-name='Optima patent collector'

gcloud projects add-iam-policy-binding "$PATENT_PROJECT" \
  --member="serviceAccount:${PATENT_SERVICE_ACCOUNT}" \
  --role='roles/bigquery.jobUser' \
  --condition=None

gcloud iam workload-identity-pools create "$PATENT_POOL" \
  --project="$PATENT_PROJECT" --location=global \
  --display-name='Optima patents AWS'

gcloud iam workload-identity-pools providers create-aws "$PATENT_PROVIDER" \
  --project="$PATENT_PROJECT" --location=global \
  --workload-identity-pool="$PATENT_POOL" \
  --account-id="$PATENT_AWS_ACCOUNT" \
  --attribute-mapping="google.subject=assertion.arn,attribute.aws_role=assertion.arn.extract('assumed-role/{role}/')" \
  --attribute-condition="assertion.account == '${PATENT_AWS_ACCOUNT}' && assertion.arn.startsWith('arn:aws:sts::${PATENT_AWS_ACCOUNT}:assumed-role/${PATENT_AWS_ROLE}/')"

gcloud iam service-accounts add-iam-policy-binding "$PATENT_SERVICE_ACCOUNT" \
  --project="$PATENT_PROJECT" \
  --role='roles/iam.workloadIdentityUser' \
  --member="principalSet://iam.googleapis.com/projects/${PATENT_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${PATENT_POOL}/attribute.aws_role/${PATENT_AWS_ROLE}"

gcloud iam workload-identity-pools create-cred-config \
  "projects/${PATENT_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${PATENT_POOL}/providers/${PATENT_PROVIDER}" \
  --service-account="$PATENT_SERVICE_ACCOUNT" \
  --aws --enable-imdsv2 \
  --output-file=optima-patents-aws.json

printf '\nSetup completed. Send this project number back to Codex: %s\n' "$PATENT_PROJECT_NUMBER"
printf 'The generated optima-patents-aws.json is a federation configuration, not a private key.\n'
