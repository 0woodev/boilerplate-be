PROJECT_ROOT := $(shell pwd)

VENV     := .venv
PYTHON   := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip

STAGE       ?= dev
CONFIG_FILE ?= ../$(STAGE).env

.PHONY: all zip-src-all zip-layer-all zip-common-src-all diff-all \
        clean-all clean-src clean-layer clean-common \
        setup local api \
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

local:
	FLASK_DEBUG=1 $(PYTHON) local_server.py

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
