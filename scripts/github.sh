#!/bin/bash
# Usage: scripts/github.sh <command> <stage> <config_file>
# Commands: setup
set -e

COMMAND="${1:?Usage: github.sh <setup> <stage> <config_file>}"
STAGE="${2:?stage required}"
CONFIG_FILE="${3:?config_file required}"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ Config file not found: $CONFIG_FILE"
  exit 1
fi

set -a && source "$CONFIG_FILE" && set +a

REPO="$GITHUB_OWNER/$PROJECT_NAME-be"

case "$COMMAND" in
  setup)
    echo "🔧 Creating GitHub Environment: $STAGE ($REPO)"
    gh api "repos/$REPO/environments/$STAGE" -X PUT --silent

    echo "📦 Setting variables for environment: $STAGE"
    gh variable set PROJECT_NAME    --env "$STAGE" --repo "$REPO" --body "$PROJECT_NAME"
    gh variable set AWS_REGION      --env "$STAGE" --repo "$REPO" --body "$AWS_REGION"
    gh variable set AWS_ACCOUNT_ID  --env "$STAGE" --repo "$REPO" --body "$AWS_ACCOUNT_ID"
    gh variable set GITHUB_OWNER    --env "$STAGE" --repo "$REPO" --body "$GITHUB_OWNER"
    gh variable set TF_STATE_BUCKET --env "$STAGE" --repo "$REPO" --body "$TF_STATE_BUCKET"
    gh variable set FE_DOMAIN       --env "$STAGE" --repo "$REPO" --body "$FE_DOMAIN"

    echo "✅ Done. Environment '$STAGE' configured for $REPO"
    ;;
  *)
    echo "❌ Unknown command: $COMMAND"
    exit 1
    ;;
esac
