import base64
import json
from enum import Enum
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key


# ──────────────────────────────────────────────────────────────
# Opaque cursor — LastEvaluatedKey 를 base64 JSON 으로 직렬화.
# 클라이언트에는 불투명 문자열로 노출되어 내부 스키마가 바뀌어도 API 가 안 깨진다.
# ──────────────────────────────────────────────────────────────
def encode_cursor(last_evaluated_key: dict | None) -> str | None:
    if not last_evaluated_key:
        return None
    return base64.urlsafe_b64encode(json.dumps(last_evaluated_key).encode()).decode()


def decode_cursor(cursor: str | None) -> dict | None:
    if not cursor:
        return None
    return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())


class QueryMethod(str, Enum):
    EQ            = "eq"
    BEGINS_WITH   = "begins_with"
    BETWEEN       = "between"
    GT            = "gt"
    GTE           = "gte"
    LT            = "lt"
    LTE           = "lte"


class DynamoClient:
    """
    저수준 stateless DynamoDB 유틸. dict in / dict out.

    상위에서는 `DynamoModel` 의 클래스 메서드 (`User.get(...)`, `User.query(...)`)
    를 통해 모델 인스턴스로 자동 매핑된다. 그 매핑이 부담되거나 ad-hoc 한
    쿼리가 필요할 때 이 클래스를 직접 호출하면 dict 으로 받을 수 있다.
    """

    _resource = None  # boto3 resource 캐시 (Lambda 콜드스타트 절감)

    # ── boto3 resource cache ──────────────────────────────────
    @classmethod
    def _table(cls, table_name: str):
        if cls._resource is None:
            cls._resource = boto3.resource("dynamodb")
        return cls._resource.Table(table_name)

    # ── CRUD ──────────────────────────────────────────────────
    @classmethod
    def get(cls, table_name: str, key: dict) -> dict | None:
        res = cls._table(table_name).get_item(Key=key)
        return res.get("Item")

    @classmethod
    def put(cls, table_name: str, item: dict) -> None:
        cls._table(table_name).put_item(Item=item)

    @classmethod
    def delete(cls, table_name: str, key: dict) -> None:
        cls._table(table_name).delete_item(Key=key)

    @classmethod
    def update(cls, table_name: str, key: dict, updates: dict[str, Any]) -> dict:
        expr_names = {f"#k{i}": k for i, k in enumerate(updates)}
        expr_values = {f":v{i}": v for i, v in enumerate(updates.values())}
        update_expr = "SET " + ", ".join(
            f"#k{i} = :v{i}" for i in range(len(updates))
        )
        res = cls._table(table_name).update_item(
            Key=key,
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        return res.get("Attributes", {})

    # ── Query / Scan ──────────────────────────────────────────
    @classmethod
    def query(
        cls,
        table_name: str,
        *,
        index_name: str | None = None,
        hash_key: str,
        hash_value,
        range_key: str | None = None,
        method: QueryMethod = QueryMethod.EQ,
        range_value=None,
        range_value2=None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> tuple[list[dict], str | None]:
        condition = Key(hash_key).eq(hash_value)
        if range_key and range_value is not None:
            condition &= cls._range_condition(
                range_key, method, range_value, range_value2,
            )

        kwargs: dict[str, Any] = {"KeyConditionExpression": condition}
        if index_name:
            kwargs["IndexName"] = index_name
        if limit:
            kwargs["Limit"] = limit
        if cursor:
            kwargs["ExclusiveStartKey"] = decode_cursor(cursor)

        res = cls._table(table_name).query(**kwargs)
        return res.get("Items", []), encode_cursor(res.get("LastEvaluatedKey"))

    @classmethod
    def scan(
        cls,
        table_name: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> tuple[list[dict], str | None]:
        kwargs: dict[str, Any] = {}
        if limit:
            kwargs["Limit"] = limit
        if cursor:
            kwargs["ExclusiveStartKey"] = decode_cursor(cursor)
        res = cls._table(table_name).scan(**kwargs)
        return res.get("Items", []), encode_cursor(res.get("LastEvaluatedKey"))

    # ── internal ──────────────────────────────────────────────
    @staticmethod
    def _range_condition(range_key: str, method: QueryMethod, value, value2):
        k = Key(range_key)
        if method == QueryMethod.EQ:           return k.eq(value)
        if method == QueryMethod.BEGINS_WITH:  return k.begins_with(value)
        if method == QueryMethod.BETWEEN:      return k.between(value, value2)
        if method == QueryMethod.GT:           return k.gt(value)
        if method == QueryMethod.GTE:          return k.gte(value)
        if method == QueryMethod.LT:           return k.lt(value)
        if method == QueryMethod.LTE:          return k.lte(value)
        raise ValueError(f"Unknown QueryMethod: {method}")
