"""DynamoDB Local 에 프로젝트 테이블 스키마 생성.

Usage:
    make local-db-init
    # 또는
    python scripts/create_local_tables.py

새 테이블 추가 시:
    1. terraform/shared/databases/main.tf 에 테이블 정의
    2. 이 파일의 TABLES dict 에 동일 스키마 미러링 (PK/SK + GSI)

DynamoDB Local 은 access_key 로 데이터셋 격리 → make local 과 동일한 creds 사용 필수.
"""
import os
import boto3


ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:8000")
PROJECT = os.environ.get("PROJECT_NAME", "boilerplate")
STAGE = os.environ.get("STAGE", "local")
REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2")


def table_name(key: str) -> str:
    return f"{PROJECT}-{STAGE}-{key}"


# 도메인별 테이블 스키마 — terraform 선언과 정확히 일치해야 함
TABLES = {
    "users": {
        "hash_key": "PK",
        "range_key": "SK",
        "gsi": [
            {"name": "ByEmail", "hash_key": "ByEmailPK", "range_key": "ByEmailSK"},
            {"name": "ByStatus", "hash_key": "ByStatusPK", "range_key": "ByStatusSK"},
        ],
    },
}


def create_table(client, name: str, spec: dict):
    attrs = [(spec["hash_key"], "S"), (spec["range_key"], "S")]
    gsi_defs = []

    for g in spec.get("gsi", []):
        attrs.append((g["hash_key"], "S"))
        if "range_key" in g:
            attrs.append((g["range_key"], "S"))

        ks = [{"AttributeName": g["hash_key"], "KeyType": "HASH"}]
        if "range_key" in g:
            ks.append({"AttributeName": g["range_key"], "KeyType": "RANGE"})
        gsi_defs.append({
            "IndexName": g["name"],
            "KeySchema": ks,
            "Projection": {"ProjectionType": "ALL"},
        })

    seen = set()
    uniq_attrs = []
    for a, t in attrs:
        if a not in seen:
            seen.add(a)
            uniq_attrs.append({"AttributeName": a, "AttributeType": t})

    kwargs = {
        "TableName": name,
        "KeySchema": [
            {"AttributeName": spec["hash_key"], "KeyType": "HASH"},
            {"AttributeName": spec["range_key"], "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": uniq_attrs,
        "BillingMode": "PAY_PER_REQUEST",
    }
    if gsi_defs:
        kwargs["GlobalSecondaryIndexes"] = gsi_defs

    try:
        client.create_table(**kwargs)
        print(f"  ✅ {name}")
    except client.exceptions.ResourceInUseException:
        print(f"  ⏭️  {name} (already exists)")


def main():
    # DynamoDB Local 은 access_key 로 데이터 격리 → 항상 로컬용 더미 creds
    client = boto3.client(
        "dynamodb",
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id="local",
        aws_secret_access_key="local",
    )
    print(f"\n🗄️  Creating tables on {ENDPOINT_URL} (project={PROJECT}, stage={STAGE})\n")

    for key, spec in TABLES.items():
        create_table(client, table_name(key), spec)

    print("\n✅ Done.\n")


if __name__ == "__main__":
    main()
