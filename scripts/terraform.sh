#!/bin/bash
# Usage: scripts/terraform.sh <command> <stage> <config_file>
# Commands: global, init, plan, apply
set -e

COMMAND="${1:?Usage: terraform.sh <global|init|plan|apply> <stage> <config_file>}"
STAGE="${2:?stage required}"
CONFIG_FILE="${3:?config_file required}"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ Config file not found: $CONFIG_FILE"
  exit 1
fi

set -a && source "$CONFIG_FILE" && set +a

TF_BACKEND_ARGS=(
  -backend-config="bucket=$TF_STATE_BUCKET"
  -backend-config="region=$AWS_REGION"
  -backend-config="dynamodb_table=$PROJECT_NAME-tf-lock"
)

TF_VAR_ARGS=(
  -var="stage=$STAGE"
  -var="project_name=$PROJECT_NAME"
  -var="aws_region=$AWS_REGION"
  -var="aws_account_id=$AWS_ACCOUNT_ID"
  -var="github_owner=$GH_OWNER"
  -var="tf_state_bucket=$TF_STATE_BUCKET"
  -var="fe_domain=$FE_DOMAIN"
  -var="domain=$DOMAIN"
  -var="be_domain=$BE_DOMAIN"
)

case "$COMMAND" in
  global)
    cd terraform/global
    terraform init \
      "${TF_BACKEND_ARGS[@]}" \
      -backend-config="key=$PROJECT_NAME/global.tfstate"
    terraform apply -auto-approve \
      -var="aws_region=$AWS_REGION"
    ;;
  init)
    cd terraform
    terraform init \
      "${TF_BACKEND_ARGS[@]}" \
      -backend-config="key=$PROJECT_NAME/$STAGE/terraform.tfstate"
    ;;
  plan)
    cd terraform
    terraform init \
      "${TF_BACKEND_ARGS[@]}" \
      -backend-config="key=$PROJECT_NAME/$STAGE/terraform.tfstate"
    terraform plan "${TF_VAR_ARGS[@]}"
    ;;
  apply)
    cd terraform
    terraform init \
      "${TF_BACKEND_ARGS[@]}" \
      -backend-config="key=$PROJECT_NAME/$STAGE/terraform.tfstate"
    terraform apply -auto-approve "${TF_VAR_ARGS[@]}"
    ;;
  *)
    echo "❌ Unknown command: $COMMAND"
    exit 1
    ;;
esac
