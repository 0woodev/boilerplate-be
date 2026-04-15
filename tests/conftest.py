import os

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "test")
    monkeypatch.setenv("STAGE", "local")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")


@pytest.fixture(autouse=True)
def _reset_dynamo_client_cache():
    """moto 가 테스트별 격리된 백엔드를 쓰므로 DynamoClient 의 boto3 resource
    캐시를 리셋해야 다음 테스트의 mock 에 연결된다."""
    from common.dynamo.client import DynamoClient
    DynamoClient._resource = None
    yield
    DynamoClient._resource = None


@pytest.fixture
def aws():
    """Moto mock 활성화."""
    with mock_aws():
        yield


def create_table(
    name: str,
    *,
    gsi: list[dict] | None = None,
):
    """표준 pk/sk 테이블 생성 헬퍼. attrs는 PK/SK + GSI에서 쓰는 것 자동 수집."""
    attrs = [("PK", "S"), ("SK", "S")]
    gsis = gsi or []
    for g in gsis:
        attrs.append((g["hash_key"], "S"))
        if "range_key" in g:
            attrs.append((g["range_key"], "S"))
    # dedupe preserving order
    seen = set()
    uniq_attrs = []
    for a, t in attrs:
        if a not in seen:
            seen.add(a)
            uniq_attrs.append((a, t))

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
