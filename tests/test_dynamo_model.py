"""Tests for DynamoModel + GSI framework.

가상 Widget 엔티티로 프레임워크 동작을 검증.
"""
from typing import ClassVar

import pytest

from common.dynamo import DynamoModel, GSI
from tests.conftest import create_table


# ──────────────────────────────────────────────────────────────
# Test models
# ──────────────────────────────────────────────────────────────
class Widget(DynamoModel):
    table_name:  ClassVar[str] = "{project_name}-{stage}-widgets"
    pk_template: ClassVar[str] = "WIDGET_ID@{widget_id}"
    sk_template: ClassVar[str] = "TYPE@profile"

    widget_id: str = ""
    color:     str = ""
    size:      str = ""
    owner_id:  str = ""

    class ByOwner(GSI):
        pk_attr:     ClassVar[str] = "ByOwnerPK"
        sk_attr:     ClassVar[str] = "ByOwnerSK"
        pk_template: ClassVar[str] = "OWNER_ID@{owner_id}"
        sk_template: ClassVar[str] = "WIDGET_ID@{widget_id}"


class Record(DynamoModel):
    """Composite SK for testing begins_with / between / gt / lt."""
    table_name:  ClassVar[str] = "{project_name}-{stage}-records"
    pk_template: ClassVar[str] = "USER_ID@{user_id}"
    sk_template: ClassVar[str] = "DATE@{date}#TYPE@{record_type}"

    user_id:     str = ""
    date:        str = ""
    record_type: str = ""
    note:        str = ""


WIDGETS_TABLE = "test-local-widgets"
RECORDS_TABLE = "test-local-records"


@pytest.fixture
def widgets_table(aws):
    create_table(
        WIDGETS_TABLE,
        gsi=[{"name": "ByOwner", "hash_key": "ByOwnerPK", "range_key": "ByOwnerSK"}],
    )


@pytest.fixture
def records_table(aws):
    create_table(RECORDS_TABLE)


# ──────────────────────────────────────────────────────────────
# to_item / from_item
# ──────────────────────────────────────────────────────────────
class TestSerialize:
    def test_to_item_builds_pk_sk_and_gsi(self):
        w = Widget(widget_id="w1", color="red", size="M", owner_id="u1")
        item = w.to_item()
        assert item["PK"] == "WIDGET_ID@w1"
        assert item["SK"] == "TYPE@profile"
        assert item["ByOwnerPK"] == "OWNER_ID@u1"
        assert item["ByOwnerSK"] == "WIDGET_ID@w1"
        # original fields preserved
        assert item["widget_id"] == "w1"
        assert item["color"] == "red"

    def test_to_item_sparse_gsi_when_fields_missing(self):
        # owner_id empty → ByOwner GSI columns skipped
        w = Widget(widget_id="w1", color="red")
        item = w.to_item()
        assert item["PK"] == "WIDGET_ID@w1"
        assert "ByOwnerPK" not in item
        assert "ByOwnerSK" not in item

    def test_from_item_strips_internal_keys(self):
        raw = {
            "PK": "WIDGET_ID@w1",
            "SK": "TYPE@profile",
            "ByOwnerPK": "OWNER_ID@u1",
            "ByOwnerSK": "WIDGET_ID@w1",
            "widget_id": "w1",
            "color": "red",
        }
        w = Widget.from_item(raw)
        assert w.widget_id == "w1"
        assert w.color == "red"
        # internal keys shouldn't leak to model_dump
        dump = w.model_dump()
        assert "PK" not in dump
        assert "ByOwnerPK" not in dump

    def test_extra_fields_preserved(self):
        raw = {
            "PK": "WIDGET_ID@w1",
            "SK": "TYPE@profile",
            "widget_id": "w1",
            "legacy_field": "old_value",
        }
        w = Widget.from_item(raw)
        dump = w.model_dump()
        assert dump["legacy_field"] == "old_value"


# ──────────────────────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────────────────────
class TestCrud:
    def test_save_and_get(self, widgets_table):
        Widget(widget_id="w1", color="red", size="M", owner_id="u1").save()
        got = Widget.get(widget_id="w1")
        assert got is not None
        assert got.color == "red"
        assert got.size == "M"

    def test_get_nonexistent_returns_none(self, widgets_table):
        assert Widget.get(widget_id="nope") is None

    def test_get_by_instance(self, widgets_table):
        Widget(widget_id="w1", color="red", owner_id="u1").save()
        proto = Widget(widget_id="w1")
        got = Widget.get(proto)
        assert got is not None
        assert got.color == "red"

    def test_delete_by_key(self, widgets_table):
        Widget(widget_id="w1", color="red").save()
        Widget.delete_by_key(widget_id="w1")
        assert Widget.get(widget_id="w1") is None

    def test_instance_delete(self, widgets_table):
        w = Widget(widget_id="w1", color="red")
        w.save()
        w.delete()
        assert Widget.get(widget_id="w1") is None

    def test_update_by_key(self, widgets_table):
        Widget(widget_id="w1", color="red", size="M").save()
        updated = Widget.update_by_key({"color": "blue"}, widget_id="w1")
        assert updated.color == "blue"
        assert updated.size == "M"
        again = Widget.get(widget_id="w1")
        assert again.color == "blue"


# ──────────────────────────────────────────────────────────────
# Query — PK / partial SK / full SK
# ──────────────────────────────────────────────────────────────
class TestQuery:
    def _seed(self):
        Record(user_id="u1", date="2024-01-15", record_type="run",  note="r1").save()
        Record(user_id="u1", date="2024-01-15", record_type="swim", note="r2").save()
        Record(user_id="u1", date="2024-02-10", record_type="run",  note="r3").save()
        Record(user_id="u2", date="2024-01-15", record_type="run",  note="other").save()

    def test_query_pk_only_returns_all_sks(self, records_table):
        self._seed()
        rs, cur = Record.query(user_id="u1")
        notes = sorted(r.note for r in rs)
        assert notes == ["r1", "r2", "r3"]
        assert cur is None

    def test_query_begins_with_on_partial_sk(self, records_table):
        self._seed()
        # date만 제공 → SK begins_with "DATE@2024-01-15#TYPE@"
        rs, _ = Record.query(user_id="u1", date="2024-01-15")
        notes = sorted(r.note for r in rs)
        assert notes == ["r1", "r2"]

    def test_query_exact_match_on_full_sk(self, records_table):
        self._seed()
        rs, _ = Record.query(user_id="u1", date="2024-01-15", record_type="run")
        assert len(rs) == 1
        assert rs[0].note == "r1"

    def test_query_between(self, records_table):
        self._seed()
        rs, _ = Record.query_between(
            user_id="u1",
            start={"date": "2024-01-01"},
            end={"date": "2024-01-31"},
        )
        notes = sorted(r.note for r in rs)
        assert notes == ["r1", "r2"]

    def test_query_gt_full_sk(self, records_table):
        self._seed()
        # SK > "DATE@2024-01-15#TYPE@run" → swim(same date, later) + 2024-02-10
        rs, _ = Record.query_gt(user_id="u1", date="2024-01-15", record_type="run")
        notes = sorted(r.note for r in rs)
        assert notes == ["r2", "r3"]

    def test_query_gt_partial_sk_includes_prefix_matches(self, records_table):
        # 주의: partial SK로 gt 하면 "prefix 이후" 를 포함 → 같은 날짜의 레코드도 포함됨.
        # 엄밀한 "date 이후" 를 원하면 full SK 를 주거나 query_between 을 사용.
        self._seed()
        rs, _ = Record.query_gt(user_id="u1", date="2024-01-15")
        # 렌더링된 prefix "DATE@2024-01-15#TYPE@" 보다 큰 모든 SK → 3건 전부
        assert len(rs) == 3

    def test_query_lt(self, records_table):
        self._seed()
        # SK < "DATE@2024-02-10#TYPE@" → 2024-01-15 의 run/swim
        rs, _ = Record.query_lt(user_id="u1", date="2024-02-10")
        notes = sorted(r.note for r in rs)
        assert notes == ["r1", "r2"]

    def test_query_with_instance(self, records_table):
        self._seed()
        proto = Record(user_id="u1", date="2024-01-15")
        rs, _ = Record.query(proto)
        assert len(rs) == 2


# ──────────────────────────────────────────────────────────────
# GSI query
# ──────────────────────────────────────────────────────────────
class TestGsiQuery:
    def test_gsi_query_eq(self, widgets_table):
        Widget(widget_id="w1", color="red",   owner_id="u1").save()
        Widget(widget_id="w2", color="blue",  owner_id="u1").save()
        Widget(widget_id="w3", color="green", owner_id="u2").save()

        rs, _ = Widget.ByOwner.query(owner_id="u1")
        widget_ids = sorted(w.widget_id for w in rs)
        assert widget_ids == ["w1", "w2"]

    def test_gsi_query_starts_with_on_sk(self, widgets_table):
        Widget(widget_id="w1",   color="red",  owner_id="u1").save()
        Widget(widget_id="w100", color="blue", owner_id="u1").save()
        Widget(widget_id="x1",   color="green", owner_id="u1").save()

        # ByOwner.sk_template = "WIDGET_ID@{widget_id}" — 단일 placeholder 이므로
        # query() 는 EQ 로 수축됨. 접두사 매칭 원하면 query_starts_with 명시.
        rs, _ = Widget.ByOwner.query_starts_with(owner_id="u1", widget_id="w")
        ids = sorted(w.widget_id for w in rs)
        assert ids == ["w1", "w100"]


# ──────────────────────────────────────────────────────────────
# Scan
# ──────────────────────────────────────────────────────────────
class TestScan:
    def test_scan_returns_all(self, records_table):
        Record(user_id="u1", date="2024-01-01", record_type="run").save()
        Record(user_id="u1", date="2024-02-02", record_type="swim").save()
        Record(user_id="u2", date="2024-03-03", record_type="bike").save()

        rs, cur = Record.scan()
        assert len(rs) == 3
        assert cur is None

    def test_scan_with_limit_paginates(self, records_table):
        for i in range(5):
            Record(user_id="u1", date=f"2024-01-0{i+1}", record_type="run").save()

        first, cursor = Record.scan(limit=2)
        assert len(first) == 2
        assert cursor is not None
        second, cursor2 = Record.scan(limit=10, cursor=cursor)
        # total should add up to 5
        assert len(first) + len(second) == 5


# ──────────────────────────────────────────────────────────────
# Pagination on query
# ──────────────────────────────────────────────────────────────
class TestPagination:
    def test_query_cursor(self, records_table):
        for i in range(5):
            Record(user_id="u1", date=f"2024-01-0{i+1}", record_type="run").save()

        page1, cur = Record.query(user_id="u1", limit=2)
        assert len(page1) == 2
        assert cur is not None
        page2, cur2 = Record.query(user_id="u1", limit=2, cursor=cur)
        assert len(page2) == 2
        # combined, no duplicates
        all_notes = {r.date for r in page1 + page2}
        assert len(all_notes) == 4
