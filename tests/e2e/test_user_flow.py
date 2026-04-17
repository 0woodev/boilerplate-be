"""E2E 시나리오 예시 — boilerplate user CRUD 전체 플로우.

실행:
    # 1. DynamoDB Local 시작
    make local-db && make local-db-init

    # 2. Flask 서버 (별도 터미널)
    make local STAGE=local

    # 3. E2E 실행
    make e2e STAGE=local

    # 또는 dev 환경 대상
    E2E_BASE_URL=https://my-api.example.com make e2e STAGE=dev
"""
import requests


class TestUserFlow:
    """User CRUD 시나리오. 각 단계가 이전 단계 결과에 의존."""

    def test_01_create_user(self, base_url, flow_state):
        r = requests.post(f"{base_url}/users", json={
            "email": "alice@example.com",
            "name": "Alice",
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["email"] == "alice@example.com"
        flow_state["user_id"] = data["user_id"]

    def test_02_get_user(self, base_url, flow_state):
        r = requests.get(f"{base_url}/users/{flow_state['user_id']}")
        assert r.status_code == 200
        assert r.json()["name"] == "Alice"

    def test_03_list_users(self, base_url, flow_state):
        r = requests.get(f"{base_url}/users")
        assert r.status_code == 200
        users = r.json()["users"]
        assert any(u["user_id"] == flow_state["user_id"] for u in users)


import pytest

@pytest.fixture(scope="class")
def flow_state():
    return {}
