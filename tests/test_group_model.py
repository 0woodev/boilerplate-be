from app.api.group.model import Group
from tests.conftest import create_table

import pytest


GROUPS_TABLE = "test-local-groups"


@pytest.fixture
def groups_table(aws):
    create_table(
        GROUPS_TABLE,
        gsi=[
            {"name": "ByOwner", "hash_key": "ByOwnerPK", "range_key": "ByOwnerSK"},
        ],
    )


class TestGroupCrud:
    def test_save_and_get(self, groups_table):
        g = Group(
            group_id="g1",
            name="Runners Club",
            description="Weekend running group",
            owner_user_id="u1",
            created_at="2024-01-15T10:00:00Z",
        )
        g.save()
        got = Group.get(group_id="g1")
        assert got is not None
        assert got.name == "Runners Club"
        assert got.owner_user_id == "u1"

    def test_delete(self, groups_table):
        Group(group_id="g1", name="test", owner_user_id="u1", created_at="2024-01-01").save()
        Group.delete_by_key(group_id="g1")
        assert Group.get(group_id="g1") is None


class TestGroupByOwner:
    def test_list_owned_groups(self, groups_table):
        Group(group_id="g1", name="A", owner_user_id="u1", created_at="2024-01-01").save()
        Group(group_id="g2", name="B", owner_user_id="u1", created_at="2024-02-01").save()
        Group(group_id="g3", name="C", owner_user_id="u2", created_at="2024-01-15").save()

        groups, _ = Group.ByOwner.query(owner_user_id="u1")
        assert sorted(g.group_id for g in groups) == ["g1", "g2"]

    def test_owned_groups_date_range(self, groups_table):
        Group(group_id="g1", name="A", owner_user_id="u1", created_at="2024-01-01").save()
        Group(group_id="g2", name="B", owner_user_id="u1", created_at="2024-06-01").save()
        Group(group_id="g3", name="C", owner_user_id="u1", created_at="2024-12-01").save()

        groups, _ = Group.ByOwner.query_between(
            owner_user_id="u1",
            start={"created_at": "2024-01-01"},
            end={"created_at": "2024-06-30"},
        )
        assert sorted(g.group_id for g in groups) == ["g1", "g2"]

    def test_owned_groups_by_year_prefix(self, groups_table):
        Group(group_id="g1", name="A", owner_user_id="u1", created_at="2023-01-01").save()
        Group(group_id="g2", name="B", owner_user_id="u1", created_at="2024-01-01").save()
        Group(group_id="g3", name="C", owner_user_id="u1", created_at="2024-06-01").save()

        # 2024년 생성 그룹만 — 단일 placeholder SK 이므로 명시적 starts_with
        groups, _ = Group.ByOwner.query_starts_with(owner_user_id="u1", created_at="2024-")
        assert sorted(g.group_id for g in groups) == ["g2", "g3"]
