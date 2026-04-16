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
    # ── Repository variables (stage 무관, 공통값) ──────────────
    echo "📦 Setting repository variables ($REPO)"
    gh variable set PROJECT_NAME    --repo "$REPO" --body "$PROJECT_NAME"
    gh variable set GH_OWNER        --repo "$REPO" --body "$GITHUB_OWNER"
    gh variable set AWS_REGION      --repo "$REPO" --body "$AWS_REGION"
    gh variable set AWS_ACCOUNT_ID  --repo "$REPO" --body "$AWS_ACCOUNT_ID"
    gh variable set TF_STATE_BUCKET --repo "$REPO" --body "$TF_STATE_BUCKET"
    gh variable set DOMAIN          --repo "$REPO" --body "$DOMAIN"

    # ── Environment variables (stage별 다른 값) ────────────────
    echo "🔧 Creating GitHub Environment: $STAGE ($REPO)"
    gh api "repos/$REPO/environments/$STAGE" -X PUT --silent

    echo "📦 Setting environment variables for: $STAGE"
    # 호스트만 — terraform custom domain 등에 사용
    gh variable set FE_DOMAIN --env "$STAGE" --repo "$REPO" --body "$FE_DOMAIN"
    gh variable set BE_DOMAIN --env "$STAGE" --repo "$REPO" --body "$BE_DOMAIN"
    # 풀 URL (https:// 포함) — CORS, 외부 응답에 사용
    gh variable set FE_URL    --env "$STAGE" --repo "$REPO" --body "$FE_URL"
    gh variable set BE_URL    --env "$STAGE" --repo "$REPO" --body "$BE_URL"

    echo "✅ Done. ($REPO / env: $STAGE)"
    ;;
  *)
    echo "❌ Unknown command: $COMMAND"
    exit 1
    ;;
esac
