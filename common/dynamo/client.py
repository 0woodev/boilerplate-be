import base64
import json
import os
from typing import Any, TypeVar

import boto3
from boto3.dynamodb.conditions import Key

from .model import DynamoModel

M = TypeVar("M", bound=DynamoModel)


# ──────────────────────────────────────────────────────────────
# Opaque cursor — LastEvaluatedKey 를 base64 JSON 으로 직렬화
# 클라이언트에는 불투명 문자열로 노출되므로 내부 스키마가 바뀌어도
# API 계약이 깨지지 않는다.
# ──────────────────────────────────────────────────────────────
def encode_cursor(last_evaluated_key: dict | None) -> str | None:
    if not last_evaluated_key:
        return None
    return base64.urlsafe_b64encode(json.dumps(last_evaluated_key).encode()).decode()


def decode_cursor(cursor: str | None) -> dict | None:
    if not cursor:
        return None
    return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())


class DynamoClient:
    """
    DynamoDB wrapper — 모델 클래스 기반 API.

    handler 코드는 `PK`, `SK`, `GSI*` 같은 내부 키를 직접 조립하지 않는다.
    모든 키 규칙은 모델 클래스(`DynamoModel` 서브클래스) 에만 존재한다.
    """

    def __init__(self, table_name: str | None = None):
        self._table = boto3.resource("dynamodb").Table(
            table_name or os.environ["TABLE_NAME"]
        )

    # ── CRUD ───────────────────────────────────────────────────
    def put(self, model: DynamoModel) -> None:
        self._table.put_item(Item=model.to_item())

    def get(self, model_cls: type[M], **key_fields) -> M | None:
        res = self._table.get_item(Key={
            "PK": model_cls.pk_of(**key_fields),
            "SK": model_cls.sk_of(**key_fields),
        })
        item = res.get("Item")
        return model_cls.from_item(item) if item else None

    def delete(self, model_cls: type[M], **key_fields) -> None:
        self._table.delete_item(Key={
            "PK": model_cls.pk_of(**key_fields),
            "SK": model_cls.sk_of(**key_fields),
        })

    def update(
        self,
        model_cls: type[M],
        updates: dict[str, Any],
        **key_fields,
    ) -> M:
        """부분 수정. 반환값은 업데이트 후의 모델 인스턴스."""
        expr_names = {f"#k{i}": k for i, k in enumerate(updates)}
        expr_values = {f":v{i}": v for i, v in enumerate(updates.values())}
        update_expr = "SET " + ", ".join(
            f"#k{i} = :v{i}" for i in range(len(updates))
        )
        res = self._table.update_item(
            Key={
                "PK": model_cls.pk_of(**key_fields),
                "SK": model_cls.sk_of(**key_fields),
            },
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        return model_cls.from_item(res.get("Attributes", {}))

    # ── Query / Scan ───────────────────────────────────────────
    def query(
        self,
        model_cls: type[M],
        *,
        gsi: str | None = None,
        pk: str | None = None,
        sk_prefix: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        **pk_fields,
    ) -> tuple[list[M], str | None]:
        """
        기본 인덱스 또는 GSI 쿼리.

        PK 값 결정 우선순위:
          1. `pk=` 로 직접 지정
          2. `**pk_fields` (예: user_id="abc") → 모델이 템플릿으로 조립
          3. GSI 의 템플릿이 placeholder 없는 고정 문자열이면 그 값 사용
        """
        pk_attr = f"{gsi}PK" if gsi else "PK"
        sk_attr = f"{gsi}SK" if gsi else "SK"

        pk_value = pk if pk is not None else self._resolve_pk(model_cls, gsi, pk_fields)
        if pk_value is None:
            raise ValueError(
                f"query: PK value not resolved for {model_cls.__name__}"
                f"{f' (gsi={gsi})' if gsi else ''}"
            )

        condition = Key(pk_attr).eq(pk_value)
        if sk_prefix:
            condition &= Key(sk_attr).begins_with(sk_prefix)

        kwargs: dict[str, Any] = {"KeyConditionExpression": condition}
        if gsi:
            kwargs["IndexName"] = gsi
        if limit:
            kwargs["Limit"] = limit
        if cursor:
            kwargs["ExclusiveStartKey"] = decode_cursor(cursor)

        res = self._table.query(**kwargs)
        items = [model_cls.from_item(it) for it in res.get("Items", [])]
        return items, encode_cursor(res.get("LastEvaluatedKey"))

    def scan(
        self,
        model_cls: type[M],
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> tuple[list[M], str | None]:
        """
        전체 스캔 — 마이그레이션용 (GSI 추가 후 재저장 등).
        단일 테이블에 여러 엔티티가 공존하므로 모델의 PK prefix 로 필터링한다.
        """
        kwargs: dict[str, Any] = {}
        if limit:
            kwargs["Limit"] = limit
        if cursor:
            kwargs["ExclusiveStartKey"] = decode_cursor(cursor)

        res = self._table.scan(**kwargs)
        pk_prefix = model_cls._PK.split("{", 1)[0]
        items = [
            model_cls.from_item(it)
            for it in res.get("Items", [])
            if it.get("PK", "").startswith(pk_prefix)
        ]
        return items, encode_cursor(res.get("LastEvaluatedKey"))

    # ── internal ───────────────────────────────────────────────
    @staticmethod
    def _resolve_pk(
        model_cls: type[DynamoModel],
        gsi: str | None,
        pk_fields: dict,
    ) -> str | None:
        if gsi:
            template = model_cls._GSI[gsi]["pk"]
        else:
            template = model_cls._PK
        if "{" not in template:
            return template
        if pk_fields:
            return template.format(**pk_fields)
        return None
