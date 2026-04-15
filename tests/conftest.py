"""pytest fixtures & helpers (tests/ 전체에 자동 로드됨).

이 파일의 목적은 테스트 격리 + 모의 AWS 환경 세팅이다.
전체 개요는 tests/README.md 참고.

요약:
  - moto = "mock + boto3" — boto3 호출을 인메모리 가짜 DynamoDB 로 리다이렉트.
  - 각 테스트는 자기만의 깨끗한 가짜 AWS 환경에서 시작한다.
  - 테스트 끝나면 가짜 테이블/데이터 자동 소멸 (teardown 필요 없음).
"""
import boto3
import pytest
from moto import mock_aws


# ──────────────────────────────────────────────────────────────────
# [fixture 1] 환경변수
#
# autouse=True → 모든 테스트에 자동 적용 (명시 요청 불필요).
# monkeypatch → 테스트 끝나면 환경변수 원래대로 복원.
#
# 왜 필요한가:
#   ① PROJECT_NAME / STAGE  — DynamoModel.table_name 템플릿 치환에 사용.
#      (e.g. "{project_name}-{stage}-users" → "test-local-users")
#   ② AWS_DEFAULT_REGION + fake credentials
#      — moto 도 boto3 의 credential 체인을 거쳐 호출되므로
#        "아무 값이라도" 설정돼 있어야 boto3 가 에러 안 냄.
#        (실제 AWS 로 가지 않으니 값 자체는 의미 없음)
# ──────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "test")
    monkeypatch.setenv("STAGE", "local")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")


# ──────────────────────────────────────────────────────────────────
# [fixture 2] DynamoClient 의 boto3 resource 캐시 리셋
#
# autouse=True — 모든 테스트 앞뒤로 실행.
#
# 문제 상황:
#   DynamoClient 는 Lambda 콜드스타트 절감용으로 boto3.resource("dynamodb")
#   를 클래스 변수 (_resource) 에 캐시한다.
#
#   moto 는 @mock_aws 컨텍스트별로 새 백엔드를 만들어내는데, 이전 테스트의
#   컨텍스트에서 생성된 resource 를 캐시가 물고 있으면 현재 테스트의
#   mock 백엔드와 연결이 안 된다 (→ ResourceNotFoundException 등).
#
# 해결:
#   테스트 시작 전/후로 캐시를 None 으로 리셋해 항상 "새 환경에서 시작".
# ──────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _reset_dynamo_client_cache():
    from common.dynamo.client import DynamoClient
    DynamoClient._resource = None
    yield
    DynamoClient._resource = None


# ──────────────────────────────────────────────────────────────────
# [fixture 3] moto mock 활성화
#
# autouse 가 아니다 — 명시적으로 요청한 테스트에서만 활성화.
# (순수 함수 테스트 등 AWS 가 불필요한 경우엔 이 fixture 안 씀)
#
# 사용 방법:
#   def test_xxx(aws):      ← 인자로 aws 를 받으면 moto 활성화
#       boto3.client(...)   ← 여기서부터 boto3 호출은 전부 moto 로 간다
#
# mock_aws() 컨텍스트 매니저:
#   - 컨텍스트 진입 시 boto3 SDK 를 monkey-patch
#   - 컨텍스트 안에서 생성한 가짜 DynamoDB 테이블 + 데이터는 메모리에만 존재
#   - 컨텍스트 종료 시 전부 폐기 (teardown 자동)
# ──────────────────────────────────────────────────────────────────
@pytest.fixture
def aws():
    with mock_aws():
        yield


# ══════════════════════════════════════════════════════════════════
# 헬퍼 — 모든 모델 테스트가 공통으로 쓰는 "가짜 테이블 생성 유틸".
#
# 주의: 이 함수는 moto 인메모리 테이블을 만든다. 실제 AWS 에 아무 영향 없음.
#       `aws` fixture 가 활성화된 컨텍스트 안에서 호출해야 한다.
# ══════════════════════════════════════════════════════════════════
def create_table(
    name: str,
    *,
    gsi: list[dict] | None = None,
):
    """
    표준 PK/SK 테이블을 moto 에 생성한다.

    Args:
        name: 테이블 이름 (예: "test-local-users")
              — 모델의 table_name 템플릿이 런타임에 렌더링한 값과 일치해야 한다.
        gsi:  GSI 스펙 리스트. 각 원소는:
                {"name": "ByEmail", "hash_key": "ByEmailPK", "range_key": "ByEmailSK"}
              range_key 는 생략 가능 (hash-only GSI).

    Notes:
        - AttributeDefinitions 는 PK/SK + 모든 GSI 키를 자동 수집해 선언.
          (DynamoDB 는 "키로 사용될 컬럼" 만 AttributeDefinitions 에 등록 필요)
        - BillingMode="PAY_PER_REQUEST" 로 용량 설정 고민 없이 생성.
        - 리턴값 없음 — 만들어만 둔다. 이후 DynamoModel.save() 등에서 사용.
    """
    # 1) PK/SK 는 고정
    attrs: list[tuple[str, str]] = [("PK", "S"), ("SK", "S")]
    gsis = gsi or []

    # 2) GSI 키 컬럼들도 AttributeDefinitions 에 추가
    for g in gsis:
        attrs.append((g["hash_key"], "S"))
        if "range_key" in g:
            attrs.append((g["range_key"], "S"))

    # 3) 중복 제거 (같은 컬럼명이 여러 GSI 에 공유될 수도 있음)
    seen = set()
    uniq_attrs = []
    for a, t in attrs:
        if a not in seen:
            seen.add(a)
            uniq_attrs.append((a, t))

    # 4) GSI 정의 구조를 DynamoDB API 스펙에 맞게 변환
    gsi_defs = []
    for g in gsis:
        ks = [{"AttributeName": g["hash_key"], "KeyType": "HASH"}]
        if "range_key" in g:
            ks.append({"AttributeName": g["range_key"], "KeyType": "RANGE"})
        gsi_defs.append({
            "IndexName": g["name"],
            "KeySchema": ks,
            "Projection": {"ProjectionType": "ALL"},
        })

    # 5) moto 에 테이블 생성 — 진짜 boto3 API 호출이지만
    #    @mock_aws 가 활성화되어 있으므로 실제 AWS 대신 moto 가 처리
    kwargs = dict(
        TableName=name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": a, "AttributeType": t} for a, t in uniq_attrs
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    if gsi_defs:
        kwargs["GlobalSecondaryIndexes"] = gsi_defs

    boto3.client("dynamodb").create_table(**kwargs)
