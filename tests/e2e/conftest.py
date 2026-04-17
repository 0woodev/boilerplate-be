"""E2E 테스트 공통 fixture.

E2E_STAGE 환경변수로 타겟 결정:
  - local : http://localhost:5001  (Flask + DynamoDB Local)
  - dev   : E2E_BASE_URL 또는 dev API Gateway URL
  - prod  : E2E_BASE_URL 필수

Usage:
    E2E_STAGE=local pytest tests/e2e/ -v
    E2E_BASE_URL=https://my-api.example.com E2E_STAGE=dev pytest tests/e2e/ -v
"""
import os

import pytest


BASE_URLS = {
    "local": "http://localhost:5001",
    "dev": None,    # E2E_BASE_URL 환경변수에서 설정
    "prod": None,
}


@pytest.fixture(scope="session")
def base_url():
    stage = os.environ.get("E2E_STAGE", "local")
    url = os.environ.get("E2E_BASE_URL") or BASE_URLS.get(stage)
    if not url:
        pytest.skip(f"E2E_BASE_URL not set for stage '{stage}'")
    return url.rstrip("/")
