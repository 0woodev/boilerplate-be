import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Any


class DynamoClient:
    def __init__(self, table_name: str | None = None):
        self._table = boto3.resource("dynamodb").Table(
            table_name or os.environ["DYNAMODB_TABLE"]
        )

    def get(self, pk: str, sk: str) -> dict | None:
        res = self._table.get_item(Key={"PK": pk, "SK": sk})
        return res.get("Item")

    def put(self, item: dict) -> None:
        self._table.put_item(Item=item)

    def delete(self, pk: str, sk: str) -> None:
        self._table.delete_item(Key={"PK": pk, "SK": sk})

    def query(self, pk: str, sk_prefix: str | None = None) -> list[dict]:
        condition = Key("PK").eq(pk)
        if sk_prefix:
            condition &= Key("SK").begins_with(sk_prefix)
        res = self._table.query(KeyConditionExpression=condition)
        return res.get("Items", [])

    def update(self, pk: str, sk: str, updates: dict[str, Any]) -> dict:
        expr = "SET " + ", ".join(f"#k{i} = :v{i}" for i in range(len(updates)))
        names = {f"#k{i}": k for i, k in enumerate(updates)}
        values = {f":v{i}": v for i, v in enumerate(updates.values())}

        res = self._table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return res.get("Attributes", {})
