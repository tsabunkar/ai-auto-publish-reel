#!/usr/bin/env bash
set -euo pipefail

TF_DIR="infrastructure/terraform"
BUILD_DIR="build"
ENVIRONMENT="${ENVIRONMENT:-prod}"

usage() {
    cat <<EOF
Usage: $0 [options]

Deploys the AWS infrastructure for the AI Auto-Publish Image In-House Server
(environment: ${ENVIRONMENT}).

Options:
  -y, --auto-approve   Skip the confirmation prompt before 'terraform apply'
      --skip-build     Reuse existing Lambda deployment packages in ${BUILD_DIR}/
  -h, --help           Show this help

Post-apply manual steps (Bedrock model access, Secrets Manager credentials, and
the IoT policy attach for the MacBook) are printed at the end.
EOF
}

AUTO_APPROVE=false
SKIP_BUILD=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -y | --auto-approve) AUTO_APPROVE=true ;;
        --skip-build) SKIP_BUILD=true ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for cmd in aws terraform poetry; do
    command -v "$cmd" >/dev/null 2>&1 || fail "'$cmd' not found in PATH"
done

[[ -f "${TF_DIR}/terraform.tfvars" ]] || fail "missing ${TF_DIR}/terraform.tfvars (create it, see DEPLOYMENT.md)"

echo "==> Verifying AWS identity"
CURRENT_ARN=$(aws sts get-caller-identity --query Arn --output text)
echo "    Identity: ${CURRENT_ARN}"
CURRENT_REGION=$(aws configure get region)
echo "    Region:   ${CURRENT_REGION:-us-east-1}"

if ! poetry self show plugins 2>/dev/null | grep -q poetry-plugin-export; then
    fail "poetry-plugin-export is not installed. Run: poetry self add poetry-plugin-export"
fi

if [[ "${SKIP_BUILD}" == "true" ]]; then
    echo "==> Skipping Lambda build (--skip-build)"
else
    echo "==> Building Lambda deployment packages"
    make build-lambdas
fi

for zip in "${BUILD_DIR}/orchestrator.zip" "${BUILD_DIR}/publisher.zip"; do
    [[ -f "$zip" ]] || fail "missing Lambda package ${zip} (run 'make build-lambdas')"
done

echo "==> Initializing Terraform"
terraform -chdir="${TF_DIR}" init -upgrade

echo "==> Terraform plan"
terraform -chdir="${TF_DIR}" plan -var-file=terraform.tfvars -input=false

if [[ "${AUTO_APPROVE}" == "false" ]]; then
    echo
    read -r -p "Apply these changes? [y/N] " ANSWER
    [[ "${ANSWER}" == "y" || "${ANSWER}" == "Y" ]] || {
        echo "Aborted."
        exit 1
    }
fi

echo "==> Applying Terraform"
terraform -chdir="${TF_DIR}" apply -var-file=terraform.tfvars -input=false -auto-approve

mkdir -p "${BUILD_DIR}"
terraform -chdir="${TF_DIR}" output > "${BUILD_DIR}/deploy.out"
echo "==> Outputs written to ${BUILD_DIR}/deploy.out"

CONTENT_BUCKET=$(terraform -chdir="${TF_DIR}" output -raw content_bucket)
IOT_ENDPOINT=$(terraform -chdir="${TF_DIR}" output -raw iot_endpoint)
ORCH_ARN=$(terraform -chdir="${TF_DIR}" output -raw orchestrator_lambda_arn)
PUB_ARN=$(terraform -chdir="${TF_DIR}" output -raw publisher_lambda_arn)

cat <<EOF

==========================================
 Deployment complete for ${ENVIRONMENT}
==========================================

  S3 bucket:              ${CONTENT_BUCKET}
  IoT endpoint:           ${IOT_ENDPOINT}
  Orchestrator Lambda:    ${ORCH_ARN}
  Publisher Lambda:       ${PUB_ARN}

NEXT STEPS (manual, see DEPLOYMENT.md):

1. Enable the Bedrock model in the us-east-1 console:
     Model access -> anthropic.claude-3-5-sonnet-20241022-v2:0

2. Populate Secrets Manager credentials:
     aws secretsmanager put-secret-value --secret-id instagram-credentials-${ENVIRONMENT} \
       --secret-string '{"access_token":"...","ig_user_id":"..."}'
     aws secretsmanager put-secret-value --secret-id linkedin-credentials-${ENVIRONMENT} \
       --secret-string '{"access_token":"...","organization_urn":"urn:li:organization:..."}'
     aws secretsmanager put-secret-value --secret-id youtube-credentials-${ENVIRONMENT} \
       --secret-string '{"access_token":"...","refresh_token":"...","client_id":"...","client_secret":"..."}'

3. Attach the IoT policy to the MacBook identity (uses the current AWS identity):
     aws iot attach-policy \
       --policy-name macbook_controller_${ENVIRONMENT} \
       --target ${CURRENT_ARN}

4. Deploy the Kali worker and run the MacBook controller — see DEPLOYMENT.md.
   Use these values in the MacBook .env:
     IOT_ENDPOINT=${IOT_ENDPOINT}
     CONTENT_BUCKET=${CONTENT_BUCKET}
     AWS_REGION=${CURRENT_REGION:-us-east-1}

==========================================
EOF
