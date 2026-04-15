import os
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict

from .client import DynamoClient, QueryMethod


class DynamoModel(BaseModel):
    """
    DynamoDB Active Record 베이스.

    서브클래스 정의 예:

        class User(DynamoModel):
            table_name: ClassVar[str] = "{project_name}-{stage}-users"
            hash_key:   ClassVar[str] = "user_id"
            # range_key: ClassVar[str | None] = None   # optional

            user_id: str = ""
            name:    str = ""
            email:   str = ""
            created_at: str = ""

    사용:

        user = User(user_id=..., name=...)
        user.save()                          # put

        user2 = User.get(user_id="abc")      # 단건 조회 → User | None
        users, cur = User.query(             # GSI/PK 쿼리 → (list[User], cursor)
            hash_value="abc",
            method=QueryMethod.BEGINS_WITH,
            range_value="2024-",
        )
        users, cur = User.scan(limit=20)     # 전체 스캔
        User.update_by_key({"name": "x"}, user_id="abc")
        User.delete_by_key(user_id="abc")
        user.delete()                        # 인스턴스에서 직접

    특징:
      - pydantic `extra="allow"` — 모델 미선언 필드도 보존 (PynamoDB 단점 해소)
      - `table_name` 은 `{project_name}-{stage}-...` 같은 템플릿. 환경변수
        `PROJECT_NAME`, `STAGE` 로 런타임 치환.
    """

    model_config = ConfigDict(extra="allow")

    # 서브클래스에서 오버라이드 (ClassVar 로 명시해야 pydantic field 로 잡히지 않음)
    table_name: ClassVar[str] = ""
    hash_key:   ClassVar[str] = ""
    range_key:  ClassVar[str | None] = None

    # ── instance methods ──────────────────────────────────────
    def save(self) -> None:
        DynamoClient.put(self._table(), self.model_dump())

    def delete(self) -> None:
        DynamoClient.delete(self._table(), self._key_from_self())

    # ── classmethod CRUD ──────────────────────────────────────
    @classmethod
    def get(cls, **key_fields) -> Self | None:
        item = DynamoClient.get(cls._table(), cls._key_from_fields(key_fields))
        return cls(**item) if item else None

    @classmethod
    def update_by_key(cls, updates: dict, **key_fields) -> Self:
        item = DynamoClient.update(
            cls._table(), cls._key_from_fields(key_fields), updates,
        )
        return cls(**item)

    @classmethod
    def delete_by_key(cls, **key_fields) -> None:
        DynamoClient.delete(cls._table(), cls._key_from_fields(key_fields))

    @classmethod
    def query(
        cls,
        *,
        index_name: str | None = None,
        hash_key: str | None = None,
        hash_value,
        range_key: str | None = None,
        method: QueryMethod = QueryMethod.EQ,
        range_value=None,
        range_value2=None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> tuple[list[Self], str | None]:
        items, next_cursor = DynamoClient.query(
            cls._table(),
            index_name=index_name,
            hash_key=hash_key or cls.hash_key,
            hash_value=hash_value,
            range_key=range_key or cls.range_key,
            method=method,
            range_value=range_value,
            range_value2=range_value2,
            limit=limit,
            cursor=cursor,
        )
        return [cls(**it) for it in items], next_cursor

    @classmethod
    def scan(
        cls,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> tuple[list[Self], str | None]:
        items, next_cursor = DynamoClient.scan(
            cls._table(), limit=limit, cursor=cursor,
        )
        return [cls(**it) for it in items], next_cursor

    # ── helpers ───────────────────────────────────────────────
    @classmethod
    def _table(cls) -> str:
        return cls.table_name.format(
            project_name=os.environ["PROJECT_NAME"],
            stage=os.environ["STAGE"],
        )

    @classmethod
    def _key_from_fields(cls, fields: dict) -> dict:
        if cls.hash_key not in fields:
            raise ValueError(
                f"{cls.__name__}: hash_key '{cls.hash_key}' required, got {list(fields)}"
            )
        key = {cls.hash_key: fields[cls.hash_key]}
        if cls.range_key:
            if cls.range_key not in fields:
                raise ValueError(
                    f"{cls.__name__}: range_key '{cls.range_key}' required"
                )
            key[cls.range_key] = fields[cls.range_key]
        return key

    def _key_from_self(self) -> dict:
        key = {self.hash_key: getattr(self, self.hash_key)}
        if self.range_key:
            key[self.range_key] = getattr(self, self.range_key)
        return key
