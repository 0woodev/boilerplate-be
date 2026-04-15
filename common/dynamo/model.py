from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict


INTERNAL_KEYS: frozenset[str] = frozenset(
    {"PK", "SK"} | {f"GSI{i}{s}" for i in range(1, 10) for s in ("PK", "SK")}
)


class DynamoModel(BaseModel):
    """
    Single-table DynamoDB 모델 베이스.

    서브클래스는 필드만 선언하고 `_PK` / `_SK` / `_GSI` 템플릿을 지정한다.

        class User(DynamoModel):
            user_id: str
            name: str
            email: str
            created_at: str

            _PK = "USER#{user_id}"
            _SK = "PROFILE"
            _GSI = {"GSI1": {"pk": "USER", "sk": "{created_at}#{user_id}"}}

    규칙:
      - PK/SK/GSI*PK/GSI*SK 는 기존 필드들의 조합으로만 만든다 (keys 는 데이터의 함수).
      - 모델에 선언되지 않은 필드도 `extra="allow"` 로 보존된다 (PynamoDB 가
        declared field 만 유지하던 단점을 해소).
      - DB 에 저장된 internal key 는 읽을 때 버리고, 저장 시 항상 `to_item()` 에서
        재생성한다. 그래서 스키마가 바뀌어도 scan -> re-put 만 돌리면 마이그레이션 끝.
    """

    model_config = ConfigDict(extra="allow")

    _PK: ClassVar[str] = ""
    _SK: ClassVar[str] = ""
    _GSI: ClassVar[dict[str, dict[str, str]]] = {}

    # ── serialization ──────────────────────────────────────────
    def to_item(self) -> dict:
        data = self.model_dump()
        data["PK"] = self._format(self._PK, data)
        data["SK"] = self._format(self._SK, data)
        for idx, spec in self._GSI.items():
            data[f"{idx}PK"] = self._format(spec["pk"], data)
            data[f"{idx}SK"] = self._format(spec["sk"], data)
        return data

    @classmethod
    def from_item(cls, item: dict) -> Self:
        return cls(**{k: v for k, v in item.items() if k not in INTERNAL_KEYS})

    # ── key factories (client 가 조회/삭제 시 사용) ────────────
    @classmethod
    def pk_of(cls, **fields) -> str:
        return cls._format(cls._PK, fields)

    @classmethod
    def sk_of(cls, **fields) -> str:
        return cls._format(cls._SK, fields)

    @classmethod
    def gsi_pk_of(cls, gsi: str, **fields) -> str:
        return cls._format(cls._GSI[gsi]["pk"], fields)

    @classmethod
    def gsi_sk_of(cls, gsi: str, **fields) -> str:
        return cls._format(cls._GSI[gsi]["sk"], fields)

    # ── internal ───────────────────────────────────────────────
    @staticmethod
    def _format(template: str, data: dict) -> str:
        return template.format(**data) if "{" in template else template
