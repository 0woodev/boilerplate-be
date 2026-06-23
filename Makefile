PROJECT_ROOT := $(shell pwd)

VENV     := .venv
PYTHON   := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip

STAGE       ?= dev
CONFIG_FILE ?= ../$(STAGE).env

PROJECT_NAME ?= my-project

.PHONY: all zip-src-all zip-layer-all zip-common-src-all diff-all \
        clean-all clean-src clean-layer clean-common \
        setup setup-dev local api test e2e \
        local-db local-db-init local-db-stop local-db-sync \
        tf-global tf-init tf-plan tf-apply \
        gh-setup

# ──────────────────────────────────────────────────────────────
# 빌드
# ──────────────────────────────────────────────────────────────
all: zip-src-all zip-layer-all zip-common-src-all

zip-src-all:
	@bash scripts/build.sh zip-src

zip-layer-all:
	@bash scripts/build.sh zip-layer

zip-common-src-all:
	@bash scripts/build.sh zip-common

diff-all:
	@bash scripts/build.sh diff

clean-all: clean-src clean-layer clean-common

clean-src:
	@bash scripts/build.sh clean-src

clean-layer:
	@bash scripts/build.sh clean-layer

clean-common:
	@bash scripts/build.sh clean-common

# ──────────────────────────────────────────────────────────────
# 로컬 개발
# ──────────────────────────────────────────────────────────────
setup:
	@if [ -d "$(VENV)" ]; then \
		echo "⏸️  .venv already exists. Skipping."; \
	else \
		echo "🐍 Creating virtual environment..."; \
		python3 -m venv $(VENV); \
		$(PIP) install -r requirements.txt -q; \
		echo "✅ Done. Run: source $(VENV)/bin/activate"; \
	fi

# dev 의존성(pytest, moto 등) 까지 설치
setup-dev: setup
	@$(PIP) install -r requirements-dev.txt -q
	@echo "✅ dev deps installed"

# STAGE=local → DynamoDB Local (Docker, port 8000)
# STAGE=dev   → 실제 AWS DynamoDB (dev 환경)
local:
	@if [ "$(STAGE)" = "local" ]; then \
		echo "🐳 Using DynamoDB Local (http://localhost:8000)"; \
		PROJECT_NAME=$(PROJECT_NAME) STAGE=local AWS_DEFAULT_REGION=ap-northeast-2 \
		AWS_ENDPOINT_URL=http://localhost:8000 \
		AWS_ACCESS_KEY_ID=local AWS_SECRET_ACCESS_KEY=local \
		FLASK_DEBUG=1 $(PYTHON) local_server.py; \
	else \
		echo "☁️  Using AWS DynamoDB ($(STAGE))"; \
		PROJECT_NAME=$(PROJECT_NAME) STAGE=$(STAGE) \
		FLASK_DEBUG=1 $(PYTHON) local_server.py; \
	fi

# DynamoDB Local 테이블 생성 (docker 실행 후 1회)
local-db:
	@mkdir -p $(PROJECT_ROOT)/.dynamodb-data
	docker run -d --name dynamodb-local \
		-p 8000:8000 \
		-v $(PROJECT_ROOT)/.dynamodb-data:/home/dynamodblocal/data \
		amazon/dynamodb-local \
		-jar DynamoDBLocal.jar -sharedDb -dbPath /home/dynamodblocal/data \
		2>/dev/null || docker start dynamodb-local
	@echo "🐳 DynamoDB Local running on http://localhost:8000"
	@echo "   💾 데이터 저장: $(PROJECT_ROOT)/.dynamodb-data/"

local-db-init:
	@$(PYTHON) scripts/create_local_tables.py

local-db-stop:
	docker stop dynamodb-local

# DB 동기화 (데이터 복사)
# Usage: make local-db-sync                    # dev → local (기본)
#        make local-db-sync FROM=prod          # prod → local
#        make local-db-sync FROM=prod TO=dev   # prod → dev (확인 프롬프트)
FROM ?= dev
TO   ?= local
local-db-sync:
	@$(PYTHON) scripts/sync_to_local.py --from $(FROM) --to $(TO)

test:
	@$(VENV)/bin/pytest tests/ --ignore=tests/e2e

# E2E 테스트: make e2e STAGE=local | dev
e2e:
	@E2E_STAGE=$(STAGE) $(VENV)/bin/pytest tests/e2e/ -v

# make api name=api_post_create_order [domain=order]
api:
	@if [ -z "$(name)" ]; then \
		echo "❌ Usage: make api name=api_post_create_item [domain=item]"; \
		exit 1; \
	fi
	@domain=$${domain:-user}; \
	path="app/api/$$domain/$(name)"; \
	mkdir -p "$$path"; \
	if [ ! -f "$$path/handler.py" ]; then \
		printf 'from common.awslambda.response_handler import ResponseHandler\nfrom common.awslambda.request_util import parse_event\n\nROUTE = ("POST", "/TODO")  # TODO: 실제 경로로 변경\n\n\n@ResponseHandler.api\ndef handler(event, context):\n    body = parse_event(event)\n    return {"message": "ok"}\n' > "$$path/handler.py"; \
		echo "✅ Created: $$path/handler.py"; \
	else \
		echo "⚠️  Already exists: $$path/handler.py (skipped)"; \
	fi

# ──────────────────────────────────────────────────────────────
# Terraform (로컬 실행 전용)
# make tf-plan STAGE=prod → ../prod.env 참조
# ──────────────────────────────────────────────────────────────
tf-global:
	@bash scripts/terraform.sh global $(STAGE) $(CONFIG_FILE)

tf-init:
	@bash scripts/terraform.sh init $(STAGE) $(CONFIG_FILE)

tf-plan:
	@bash scripts/terraform.sh plan $(STAGE) $(CONFIG_FILE)

tf-apply:
	@bash scripts/terraform.sh apply $(STAGE) $(CONFIG_FILE)

# ──────────────────────────────────────────────────────────────
# GitHub 설정
# make gh-setup STAGE=prod → ../prod.env 참조
# ──────────────────────────────────────────────────────────────
gh-setup:
	@bash scripts/github.sh setup $(STAGE) $(CONFIG_FILE)
