"""DynamoDB Local에 테이블 생성.

Usage:
    python scripts/create_local_tables.py
    # 또는
    make local-db-init
"""
import os

import boto3


ENDPOINT_URL = "http://localhost:8000"
PROJECT = os.environ.get("PROJECT_NAME", "my-project")
STAGE = "local"


def table_name(key: str) -> str:
    return f"{PROJECT}-{STAGE}-{key}"


# GSI 정의는 terraform/shared/databases/main.tf 와 1:1 일치해야 함.
TABLES = {
    "users": {
        "hash_key": "PK",
        "range_key": "SK",
        "gsi": [
            {"name": "ByEmail", "hash_key": "ByEmailPK", "range_key": "ByEmailSK"},
            {"name": "ByStatus", "hash_key": "ByStatusPK", "range_key": "ByStatusSK"},
        ],
    },
    "groups": {
        "hash_key": "PK",
        "range_key": "SK",
        "gsi": [
            {"name": "ByOwner", "hash_key": "ByOwnerPK", "range_key": "ByOwnerSK"},
        ],
    },
    "members": {
        "hash_key": "PK",
        "range_key": "SK",
        "gsi": [
            {"name": "ByUser", "hash_key": "ByUserPK", "range_key": "ByUserSK"},
            {"name": "ByRole", "hash_key": "ByRolePK", "range_key": "ByRoleSK"},
        ],
    },
    "patch-notes": {
        "hash_key": "PK",
        "range_key": "SK",
        "gsi": [
            {"name": "ByDate", "hash_key": "ByDatePK", "range_key": "ByDateSK"},
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
        # 기존 테이블이 있으면 drop 후 재생성 (로컬 스키마 drift 방지)
        print(f"  ♻️  {name} (exists → dropping and recreating)")
        client.delete_table(TableName=name)
        waiter = client.get_waiter("table_not_exists")
        waiter.wait(TableName=name)
        client.create_table(**kwargs)
        print(f"  ✅ {name} (recreated)")


def main():
    # DynamoDB Local은 access_key로 데이터셋 격리 → Flask와 동일한 creds 사용
    client = boto3.client(
        "dynamodb",
        endpoint_url=ENDPOINT_URL,
        region_name="ap-northeast-2",
        aws_access_key_id="local",
        aws_secret_access_key="local",
    )
    print(f"\n🗄️  Creating tables on {ENDPOINT_URL}\n")

    for key, spec in TABLES.items():
        create_table(client, table_name(key), spec)

    print("\n✅ Done.\n")


if __name__ == "__main__":
    main()
