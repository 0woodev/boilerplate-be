"""DynamoModel + GSI framework 테스트.

이 파일은 "프레임워크 자체" 를 검증한다. 도메인 모델(User/Group/Member) 이 아니라,
가상의 Widget, Record 를 만들어 템플릿 렌더링·GSI 자동 생성·쿼리 동작을 확인한다.

구성:
  - Widget : 단순 PK/SK + 하나의 GSI (ByOwner). 기본 CRUD/GSI 시나리오.
  - Record : composite SK ("DATE@{date}#TYPE@{record_type}") — begins_with/between/gt/lt 시나리오.

전체 배경은 tests/README.md 참고.
  - moto = boto3 의 인메모리 가짜 구현 (실제 AWS 안 감)
  - conftest.py 의 `aws` fixture 가 moto 활성화
  - conftest.py 의 `create_table` 헬퍼가 테스트용 가짜 테이블 생성
"""
from typing import ClassVar

import pytest

from common.dynamo import DynamoModel, GSI
from tests.conftest import create_table


# ══════════════════════════════════════════════════════════════════
# Test Models — 실제 도메인 모델이 아닌, 프레임워크 검증용 fixture 모델
# ══════════════════════════════════════════════════════════════════

class Widget(DynamoModel):
    """단순 PK/SK + GSI 1개 — 기본 시나리오 검증용."""

    table_name:  ClassVar[str] = "{project_name}-{stage}-widgets"
    pk_template: ClassVar[str] = "WIDGET_ID@{widget_id}"
    sk_template: ClassVar[str] = "TYPE@profile"   # 고정 SK (엔티티당 하나)

    widget_id: str = ""
    color:     str = ""
    size:      str = ""
    owner_id:  str = ""

    # "소유자별 위젯 리스팅" 용 GSI
    class ByOwner(GSI):
        pk_attr:     ClassVar[str] = "ByOwnerPK"
        sk_attr:     ClassVar[str] = "ByOwnerSK"
        pk_template: ClassVar[str] = "OWNER_ID@{owner_id}"
        sk_template: ClassVar[str] = "WIDGET_ID@{widget_id}"


class Record(DynamoModel):
    """Composite SK (두 개 필드 조합) — begins_with/between/gt/lt 검증용."""

    table_name:  ClassVar[str] = "{project_name}-{stage}-records"
    pk_template: ClassVar[str] = "USER_ID@{user_id}"
    sk_template: ClassVar[str] = "DATE@{date}#TYPE@{record_type}"

    user_id:     str = ""
    date:        str = ""
    record_type: str = ""
    note:        str = ""


# 실제 DynamoDB 에 들어갈 테이블명 — 모델의 table_name 이 PROJECT_NAME=test, STAGE=local 로 렌더링된 결과
WIDGETS_TABLE = "test-local-widgets"
RECORDS_TABLE = "test-local-records"


# ══════════════════════════════════════════════════════════════════
# Fixtures — 테이블별로 moto 인메모리 테이블을 세팅
# ══════════════════════════════════════════════════════════════════

@pytest.fixture
def widgets_table(aws):
    """Widget 용 가짜 테이블. `aws` 를 의존성으로 받아 moto 활성화된 상태에서 생성."""
    create_table(
        WIDGETS_TABLE,
        gsi=[{"name": "ByOwner", "hash_key": "ByOwnerPK", "range_key": "ByOwnerSK"}],
    )


@pytest.fixture
def records_table(aws):
    """Record 용 가짜 테이블. GSI 없음."""
    create_table(RECORDS_TABLE)


# ══════════════════════════════════════════════════════════════════
# to_item / from_item — 직렬화/역직렬화는 DB 안 건드리는 순수 로직
# (이 테스트들은 aws fixture 불필요)
# ══════════════════════════════════════════════════════════════════

class TestSerialize:
    def test_to_item_builds_pk_sk_and_gsi(self):
        """save() 시 모델이 PK/SK + 모든 GSI 키를 자동으로 채워 dict 로 변환하는지."""
        w = Widget(widget_id="w1", color="red", size="M", owner_id="u1")
        item = w.to_item()

        # 기본 테이블 키 — 템플릿 렌더링 결과
        assert item["PK"] == "WIDGET_ID@w1"
        assert item["SK"] == "TYPE@profile"

        # GSI 키 — Widget.ByOwner 정의된 대로 자동 생성
        assert item["ByOwnerPK"] == "OWNER_ID@u1"
        assert item["ByOwnerSK"] == "WIDGET_ID@w1"

        # 원본 필드도 그대로 포함 (PK/SK 에 담겨도 별도 컬럼으로 유지)
        assert item["widget_id"] == "w1"
        assert item["color"] == "red"

    def test_to_item_sparse_gsi_when_fields_missing(self):
        """owner_id 가 비었을 때, ByOwner GSI 컬럼은 저장에서 빠져야 함 (sparse index)."""
        w = Widget(widget_id="w1", color="red")  # owner_id 없음

        item = w.to_item()
        assert item["PK"] == "WIDGET_ID@w1"
        # ByOwner.pk_template 이 {owner_id} 를 필요로 하는데 비었으므로
        # 해당 GSI 컬럼은 아예 저장되지 않음 → DynamoDB 에선 이 아이템이 ByOwner GSI 에서 빠짐
        assert "ByOwnerPK" not in item
        assert "ByOwnerSK" not in item

    def test_from_item_strips_internal_keys(self):
        """DB 에서 읽어올 때 PK/SK/GSI 키들은 모델 인스턴스의 필드로 가져오지 않음."""
        raw = {
            "PK": "WIDGET_ID@w1",
            "SK": "TYPE@profile",
            "ByOwnerPK": "OWNER_ID@u1",
            "ByOwnerSK": "WIDGET_ID@w1",
            "widget_id": "w1",
            "color": "red",
        }
        w = Widget.from_item(raw)

        # 비즈니스 필드는 들어옴
        assert w.widget_id == "w1"
        assert w.color == "red"

        # PK/SK/GSI 는 model_dump() 에 노출되지 않음 — 내부 키니까
        dump = w.model_dump()
        assert "PK" not in dump
        assert "ByOwnerPK" not in dump

    def test_extra_fields_preserved(self):
        """모델에 선언되지 않은 필드도 (pydantic extra='allow') 유지돼야 함.
        (PynamoDB 가 declared field 외 버리던 단점 해소)"""
        raw = {
            "PK": "WIDGET_ID@w1",
            "SK": "TYPE@profile",
            "widget_id": "w1",
            "legacy_field": "old_value",  # 모델에 없는 필드
        }
        w = Widget.from_item(raw)
        dump = w.model_dump()
        assert dump["legacy_field"] == "old_value"


# ══════════════════════════════════════════════════════════════════
# CRUD — 실제 moto DynamoDB 에 저장/조회/수정/삭제
# ══════════════════════════════════════════════════════════════════

class TestCrud:
    def test_save_and_get(self, widgets_table):
        """save() → get() 왕복."""
        Widget(widget_id="w1", color="red", size="M", owner_id="u1").save()

        got = Widget.get(widget_id="w1")  # PK/SK 템플릿으로 자동 키 조립
        assert got is not None
        assert got.color == "red"
        assert got.size == "M"

    def test_get_nonexistent_returns_none(self, widgets_table):
        """없는 아이템 조회는 None."""
        assert Widget.get(widget_id="nope") is None

    def test_get_by_instance(self, widgets_table):
        """인스턴스를 키 추출 대상으로 전달 가능 (model_dump(exclude_unset=True) 로 필드 추출)."""
        Widget(widget_id="w1", color="red", owner_id="u1").save()

        proto = Widget(widget_id="w1")  # 키 필드만 채운 프로토타입
        got = Widget.get(proto)
        assert got is not None
        assert got.color == "red"

    def test_delete_by_key(self, widgets_table):
        Widget(widget_id="w1", color="red").save()
        Widget.delete_by_key(widget_id="w1")
        assert Widget.get(widget_id="w1") is None

    def test_instance_delete(self, widgets_table):
        """인스턴스 메서드로도 삭제 가능."""
        w = Widget(widget_id="w1", color="red")
        w.save()
        w.delete()
        assert Widget.get(widget_id="w1") is None

    def test_update_by_key(self, widgets_table):
        """부분 수정 — 지정한 필드만 변경, 나머지는 유지."""
        Widget(widget_id="w1", color="red", size="M").save()

        updated = Widget.update_by_key({"color": "blue"}, widget_id="w1")
        assert updated.color == "blue"
        assert updated.size == "M"  # 건드리지 않은 필드 유지

        # DB 에 반영된 값 재조회
        again = Widget.get(widget_id="w1")
        assert again.color == "blue"


# ══════════════════════════════════════════════════════════════════
# Query — composite SK 기반 다양한 쿼리 패턴
# ══════════════════════════════════════════════════════════════════

class TestQuery:
    def _seed(self):
        """각 쿼리 테스트마다 시드 데이터를 넣는 헬퍼.
        SK 값:
          r1: DATE@2024-01-15#TYPE@run
          r2: DATE@2024-01-15#TYPE@swim
          r3: DATE@2024-02-10#TYPE@run
          u2의 r: DATE@2024-01-15#TYPE@run   (다른 파티션)
        """
        Record(user_id="u1", date="2024-01-15", record_type="run",  note="r1").save()
        Record(user_id="u1", date="2024-01-15", record_type="swim", note="r2").save()
        Record(user_id="u1", date="2024-02-10", record_type="run",  note="r3").save()
        Record(user_id="u2", date="2024-01-15", record_type="run",  note="other").save()

    def test_query_pk_only_returns_all_sks(self, records_table):
        """PK 만 제공 → SK 조건 없음 → 그 PK 의 모든 아이템."""
        self._seed()
        rs, cur = Record.query(user_id="u1")
        notes = sorted(r.note for r in rs)
        assert notes == ["r1", "r2", "r3"]
        assert cur is None

    def test_query_begins_with_on_partial_sk(self, records_table):
        """composite SK 중 앞부분(date)만 제공 → 나머지 placeholder 까지 prefix 로 begins_with.
        렌더 결과: "DATE@2024-01-15#TYPE@" (record_type 이 없어서 stop)"""
        self._seed()
        rs, _ = Record.query(user_id="u1", date="2024-01-15")
        notes = sorted(r.note for r in rs)
        assert notes == ["r1", "r2"]

    def test_query_exact_match_on_full_sk(self, records_table):
        """composite SK 전체 필드 제공 → 정확히 일치 검색."""
        self._seed()
        rs, _ = Record.query(user_id="u1", date="2024-01-15", record_type="run")
        assert len(rs) == 1
        assert rs[0].note == "r1"

    def test_query_between(self, records_table):
        """SK 범위 조회 — start/end 두 dict 로 경계를 지정."""
        self._seed()
        rs, _ = Record.query_between(
            user_id="u1",
            start={"date": "2024-01-01"},  # SK 하한: "DATE@2024-01-01#TYPE@"
            end={"date": "2024-01-31"},    # SK 상한: "DATE@2024-01-31#TYPE@"
        )
        notes = sorted(r.note for r in rs)
        assert notes == ["r1", "r2"]

    def test_query_gt_full_sk(self, records_table):
        """SK 의 모든 필드 제공 → 그보다 큰 SK (strict >)."""
        self._seed()
        # SK > "DATE@2024-01-15#TYPE@run" 인 것:
        #   r2 (같은 날짜, "swim" > "run")
        #   r3 (다음 날짜)
        rs, _ = Record.query_gt(user_id="u1", date="2024-01-15", record_type="run")
        notes = sorted(r.note for r in rs)
        assert notes == ["r2", "r3"]

    def test_query_gt_partial_sk_includes_prefix_matches(self, records_table):
        """⚠️ 주의사항 테스트 — partial SK 로 gt 했을 때 "같은 prefix" 도 포함됨.
        의도가 "2024-01-15 이후의 날짜" 라면, 이 쿼리는 오인에 가까움.
        엄밀히 하려면 full SK 를 주거나 query_between 을 써야 한다."""
        self._seed()
        # 렌더 결과: "DATE@2024-01-15#TYPE@" — 이보다 sort 순으로 큰 모든 SK
        # "DATE@2024-01-15#TYPE@run" 은 이 prefix 보다 길고 큼 → 포함됨
        rs, _ = Record.query_gt(user_id="u1", date="2024-01-15")
        assert len(rs) == 3  # r1, r2, r3 전부 prefix 보다 큼

    def test_query_lt(self, records_table):
        """SK < threshold — 지정값 이전."""
        self._seed()
        rs, _ = Record.query_lt(user_id="u1", date="2024-02-10")
        notes = sorted(r.note for r in rs)
        assert notes == ["r1", "r2"]

    def test_query_with_instance(self, records_table):
        """인스턴스의 set 된 필드를 키로 사용 (fields dict 대신)."""
        self._seed()
        proto = Record(user_id="u1", date="2024-01-15")  # 부분 SK
        rs, _ = Record.query(proto)
        assert len(rs) == 2


# ══════════════════════════════════════════════════════════════════
# GSI — 중첩 클래스로 선언한 보조 인덱스 쿼리
# ══════════════════════════════════════════════════════════════════

class TestGsiQuery:
    def test_gsi_query_eq(self, widgets_table):
        """GSI 쿼리 = main 테이블 쿼리와 동일한 API, IndexName 만 다름."""
        Widget(widget_id="w1", color="red",   owner_id="u1").save()
        Widget(widget_id="w2", color="blue",  owner_id="u1").save()
        Widget(widget_id="w3", color="green", owner_id="u2").save()

        rs, _ = Widget.ByOwner.query(owner_id="u1")  # ByOwnerPK = "OWNER_ID@u1" 으로 조회
        widget_ids = sorted(w.widget_id for w in rs)
        assert widget_ids == ["w1", "w2"]

    def test_gsi_query_starts_with_on_sk(self, widgets_table):
        """단일 placeholder SK 에서 접두사 매칭을 원할 때는 query_starts_with 명시.
        query() 는 "완전 렌더" 판단 시 EQ 로 수축하기 때문."""
        Widget(widget_id="w1",   color="red",   owner_id="u1").save()
        Widget(widget_id="w100", color="blue",  owner_id="u1").save()
        Widget(widget_id="x1",   color="green", owner_id="u1").save()

        # Widget.ByOwner.sk_template = "WIDGET_ID@{widget_id}" — placeholder 1개
        # widget_id="w" 를 주면 render_full 기준 "완료" 라 query() 는 EQ → 아무것도 안 맞음
        # 접두사 의도를 명시하려면 query_starts_with
        rs, _ = Widget.ByOwner.query_starts_with(owner_id="u1", widget_id="w")
        ids = sorted(w.widget_id for w in rs)
        assert ids == ["w1", "w100"]


# ══════════════════════════════════════════════════════════════════
# Scan — 테이블 전체 (리스팅/마이그레이션용)
# ══════════════════════════════════════════════════════════════════

class TestScan:
    def test_scan_returns_all(self, records_table):
        Record(user_id="u1", date="2024-01-01", record_type="run").save()
        Record(user_id="u1", date="2024-02-02", record_type="swim").save()
        Record(user_id="u2", date="2024-03-03", record_type="bike").save()

        rs, cur = Record.scan()
        assert len(rs) == 3
        assert cur is None  # 다 가져와서 다음 페이지 없음

    def test_scan_with_limit_paginates(self, records_table):
        """limit 초과분은 cursor 로 다음 호출에서 이어받음."""
        for i in range(5):
            Record(user_id="u1", date=f"2024-01-0{i+1}", record_type="run").save()

        first, cursor = Record.scan(limit=2)
        assert len(first) == 2
        assert cursor is not None  # 더 있음

        second, _ = Record.scan(limit=10, cursor=cursor)
        assert len(first) + len(second) == 5


# ══════════════════════════════════════════════════════════════════
# Pagination — query 도 cursor 지원
# ══════════════════════════════════════════════════════════════════

class TestPagination:
    def test_query_cursor(self, records_table):
        for i in range(5):
            Record(user_id="u1", date=f"2024-01-0{i+1}", record_type="run").save()

        page1, cur = Record.query(user_id="u1", limit=2)
        assert len(page1) == 2
        assert cur is not None

        page2, _ = Record.query(user_id="u1", limit=2, cursor=cur)
        assert len(page2) == 2

        # 두 페이지 합쳐 겹침 없는지 확인
        all_dates = {r.date for r in page1 + page2}
        assert len(all_dates) == 4
