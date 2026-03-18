PROJECT_ROOT := $(shell pwd)

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: all zip-src-all zip-layer-all zip-common-src-all diff-all clean-all clean-src clean-layer clean-common setup local api

# Lambda 핸들러 디렉토리: app/api/{domain}/api_*
ZIP_TARGET_DIRS := $(shell find app/api -mindepth 3 -maxdepth 3 -type d -name "api_*" 2>/dev/null)

# 공통 코드 Layer
ZIP_COMMON_SRC_DIR := common

# 제외 패턴 (find -not \( ... \) 용)
EXCLUDE_PATTERNS := \
	-name "*.zip" -o \
	-name "*.sha" -o \
	-name "*.sha.tmp" -o \
	-name "*.pyc" -o \
	-name ".DS_Store" -o \
	-name "Makefile" -o \
	-path "*__pycache__*"

# ──────────────────────────────────────────────────────────────
# venv 셋업
# ──────────────────────────────────────────────────────────────
setup:
	@if [ -d "$(VENV)" ]; then \
		echo "⏸️  .venv already exists. Skipping."; \
	else \
		echo "🐍 Creating virtual environment..."; \
		python3 -m venv $(VENV); \
		echo "📦 Installing dependencies..."; \
		$(PIP) install -r requirements.txt -q; \
		echo "✅ Done. Run: source $(VENV)/bin/activate"; \
	fi

# ──────────────────────────────────────────────────────────────
all: zip-src-all zip-layer-all zip-common-src-all

# ──────────────────────────────────────────────────────────────
# Lambda 핸들러 zip (endpoint별 개별 build.zip)
# ──────────────────────────────────────────────────────────────
zip-src-all:
	@for dir in $(ZIP_TARGET_DIRS); do \
		echo "\n📦 Zipping: $$dir"; \
		BUILD_DIR="$(PROJECT_ROOT)/.build/$$dir"; \
		BUILD_ZIP="$$BUILD_DIR/build.zip"; \
		BUILD_SHA="$$BUILD_DIR/build.sha"; \
		BUILD_TMP="$$BUILD_DIR/build.sha.tmp"; \
		mkdir -p "$$BUILD_DIR"; \
		\
		find $$dir -type f ! \( $(EXCLUDE_PATTERNS) \) -print0 \
			| xargs -0 shasum -a 256 \
			| awk '{ print $$1 }' \
			| shasum -a 256 \
			| awk '{ print $$1 }' > $$BUILD_TMP; \
		\
		if [ -f "$$BUILD_SHA" ]; then \
			OLD=$$(cat $$BUILD_SHA); NEW=$$(cat $$BUILD_TMP); \
			if [ "$$OLD" = "$$NEW" ]; then \
				echo "⏸️  No changes. Skipping."; \
				rm -f $$BUILD_TMP; \
				continue; \
			fi; \
		fi; \
		mv $$BUILD_TMP $$BUILD_SHA; \
		\
		cd $$dir && zip -qr "$$BUILD_ZIP" . \
			-x "*.zip" -x "*.sha" -x "*__pycache__*" -x "*.pyc" -x ".DS_Store"; \
		cd "$(PROJECT_ROOT)"; \
		echo "✅ Zipped $$dir → $$BUILD_ZIP"; \
	done

# ──────────────────────────────────────────────────────────────
# 의존성 Layer zip (requirements.txt → pip install)
# ──────────────────────────────────────────────────────────────
zip-layer-all:
	@echo "\n📦 Building layer from requirements.txt"; \
	BUILD_DIR="$(PROJECT_ROOT)/.build/layer"; \
	BUILD_ZIP="$$BUILD_DIR/layer.zip"; \
	BUILD_SHA="$$BUILD_DIR/layer.sha"; \
	BUILD_TMP="$$BUILD_DIR/layer.sha.tmp"; \
	mkdir -p "$$BUILD_DIR"; \
	\
	shasum -a 256 requirements.txt | awk '{ print $$1 }' > $$BUILD_TMP; \
	\
	if [ -f "$$BUILD_SHA" ]; then \
		OLD=$$(cat $$BUILD_SHA); NEW=$$(cat $$BUILD_TMP); \
		if [ "$$OLD" = "$$NEW" ]; then \
			echo "⏸️  No changes. Skipping."; \
			rm -f $$BUILD_TMP; \
			exit 0; \
		fi; \
	fi; \
	mv $$BUILD_TMP $$BUILD_SHA; \
	\
	rm -rf "$$BUILD_DIR/python"; \
	mkdir -p "$$BUILD_DIR/python"; \
	pip install -r requirements.txt -t "$$BUILD_DIR/python" -q; \
	cd "$$BUILD_DIR" && zip -qr layer.zip python/ && du -h layer.zip; \
	rm -rf "$$BUILD_DIR/python"; \
	echo "✅ Built layer → $$BUILD_ZIP"

# ──────────────────────────────────────────────────────────────
# 공통 코드 Layer zip (common/ → python/common/)
# ──────────────────────────────────────────────────────────────
zip-common-src-all:
	@echo "\n📦 Zipping: $(ZIP_COMMON_SRC_DIR)"; \
	BUILD_DIR="$(PROJECT_ROOT)/.build/common"; \
	BUILD_ZIP="$$BUILD_DIR/layer.zip"; \
	BUILD_SHA="$$BUILD_DIR/layer.sha"; \
	BUILD_TMP="$$BUILD_DIR/layer.sha.tmp"; \
	mkdir -p "$$BUILD_DIR"; \
	\
	find $(ZIP_COMMON_SRC_DIR) -type f ! \( $(EXCLUDE_PATTERNS) \) -print0 \
		| xargs -0 shasum -a 256 \
		| awk '{ print $$1 }' \
		| shasum -a 256 \
		| awk '{ print $$1 }' > $$BUILD_TMP; \
	\
	if [ -f "$$BUILD_SHA" ]; then \
		OLD=$$(cat $$BUILD_SHA); NEW=$$(cat $$BUILD_TMP); \
		if [ "$$OLD" = "$$NEW" ]; then \
			echo "⏸️  No changes. Skipping."; \
			rm -f $$BUILD_TMP; \
			exit 0; \
		fi; \
	fi; \
	mv $$BUILD_TMP $$BUILD_SHA; \
	\
	rm -rf "$$BUILD_DIR/python"; \
	mkdir -p "$$BUILD_DIR/python"; \
	cp -r $(ZIP_COMMON_SRC_DIR) "$$BUILD_DIR/python/"; \
	cd "$$BUILD_DIR" && zip -qr layer.zip python/ \
		-x "*__pycache__*" -x "*.pyc" -x "*.zip" -x "*.sha"; \
	rm -rf "$$BUILD_DIR/python"; \
	echo "✅ Zipped common → $$BUILD_ZIP"

# ──────────────────────────────────────────────────────────────
# 변경 감지 (zip 생성 없이 diff만 출력)
# ──────────────────────────────────────────────────────────────
diff-all:
	@for dir in $(ZIP_TARGET_DIRS); do \
		BUILD_DIR="$(PROJECT_ROOT)/.build/$$dir"; \
		BUILD_SHA="$$BUILD_DIR/build.sha"; \
		BUILD_TMP="$$BUILD_DIR/build.sha.tmp"; \
		mkdir -p "$$BUILD_DIR"; \
		\
		find $$dir -type f ! \( $(EXCLUDE_PATTERNS) \) -print0 \
			| xargs -0 shasum -a 256 \
			| awk '{ print $$1 }' \
			| shasum -a 256 \
			| awk '{ print $$1 }' > $$BUILD_TMP; \
		\
		if [ -f "$$BUILD_SHA" ]; then \
			OLD=$$(cat $$BUILD_SHA); NEW=$$(cat $$BUILD_TMP); \
			if [ "$$OLD" != "$$NEW" ]; then \
				echo "🟡 Changed:   $$dir"; \
			else \
				echo "🟢 No change: $$dir"; \
			fi; \
		else \
			echo "🆕 No SHA yet: $$dir"; \
		fi; \
		rm -f $$BUILD_TMP; \
	done

# ──────────────────────────────────────────────────────────────
# 로컬 Flask 서버
# ──────────────────────────────────────────────────────────────
local:
	FLASK_ENV=development $(PYTHON) local_server.py

# ──────────────────────────────────────────────────────────────
# 새 API 핸들러 스캐폴딩
# Usage: make api name=api_post_create_item [domain=item]
# ──────────────────────────────────────────────────────────────
api:
	@if [ -z "$(name)" ]; then \
		echo "❌ Error: missing 'name'"; \
		echo "Usage: make api name=api_post_create_item [domain=item]"; \
		exit 1; \
	fi; \
	domain=$${domain:-user}; \
	path="app/api/$$domain/$(name)"; \
	mkdir -p "$$path"; \
	if [ ! -f "$$path/handler.py" ]; then \
		printf 'from common.awslambda.response_handler import ResponseHandler\nfrom common.awslambda.request_util import parse_event\n\nROUTE = ("POST", "/TODO")  # TODO: 실제 경로로 변경\n\n\n@ResponseHandler.api\ndef handler(event, context):\n    body = parse_event(event)\n    return {"message": "ok"}\n' > "$$path/handler.py"; \
		echo "✅ Created: $$path/handler.py"; \
	else \
		echo "⚠️  Already exists: $$path/handler.py (skipped)"; \
	fi

# ──────────────────────────────────────────────────────────────
clean-all: clean-src clean-layer clean-common

clean-src:
	@for dir in $(ZIP_TARGET_DIRS); do \
		echo "🧹 Cleaning: $$dir"; \
		rm -f "$(PROJECT_ROOT)/.build/$$dir/build.zip" \
		      "$(PROJECT_ROOT)/.build/$$dir/build.sha" \
		      "$(PROJECT_ROOT)/.build/$$dir/build.sha.tmp"; \
	done

clean-layer:
	@rm -rf "$(PROJECT_ROOT)/.build/layer"
	@echo "🧹 Cleaned layer"

clean-common:
	@rm -rf "$(PROJECT_ROOT)/.build/common"
	@echo "🧹 Cleaned common"
