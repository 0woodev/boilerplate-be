from app.api.member.model import Member
from tests.conftest import create_table

import pytest


MEMBERS_TABLE = "test-local-members"


@pytest.fixture
def members_table(aws):
    create_table(
        MEMBERS_TABLE,
        gsi=[
            {"name": "ByUser", "hash_key": "ByUserPK", "range_key": "ByUserSK"},
            {"name": "ByRole", "hash_key": "ByRolePK", "range_key": "ByRoleSK"},
        ],
    )


class TestMemberCrud:
    def test_save_and_get(self, members_table):
        m = Member(
            group_id="g1",
            user_id="u1",
            role="owner",
            joined_at="2024-01-15T10:00:00Z",
        )
        m.save()
        got = Member.get(group_id="g1", user_id="u1")
        assert got is not None
        assert got.role == "owner"

    def test_delete(self, members_table):
        Member(group_id="g1", user_id="u1", role="member", joined_at="2024-01-01").save()
        Member.delete_by_key(group_id="g1", user_id="u1")
        assert Member.get(group_id="g1", user_id="u1") is None


class TestMembersOfGroup:
    def test_list_members_of_group(self, members_table):
        Member(group_id="g1", user_id="u1", role="owner",  joined_at="2024-01-01").save()
        Member(group_id="g1", user_id="u2", role="admin",  joined_at="2024-01-02").save()
        Member(group_id="g1", user_id="u3", role="member", joined_at="2024-01-03").save()
        Member(group_id="g2", user_id="u1", role="member", joined_at="2024-01-04").save()

        ms, _ = Member.query(group_id="g1")
        assert sorted(m.user_id for m in ms) == ["u1", "u2", "u3"]


class TestByUser:
    def test_groups_user_belongs_to(self, members_table):
        Member(group_id="g1", user_id="u1", role="owner",  joined_at="2024-01-01").save()
        Member(group_id="g2", user_id="u1", role="member", joined_at="2024-01-02").save()
        Member(group_id="g3", user_id="u2", role="member", joined_at="2024-01-03").save()

        ms, _ = Member.ByUser.query(user_id="u1")
        assert sorted(m.group_id for m in ms) == ["g1", "g2"]


class TestByRole:
    def test_admins_of_group(self, members_table):
        Member(group_id="g1", user_id="u1", role="owner",  joined_at="2024-01-01").save()
        Member(group_id="g1", user_id="u2", role="admin",  joined_at="2024-01-02").save()
        Member(group_id="g1", user_id="u3", role="admin",  joined_at="2024-01-03").save()
        Member(group_id="g1", user_id="u4", role="member", joined_at="2024-01-04").save()

        admins, _ = Member.ByRole.query(group_id="g1", role="admin")
        assert sorted(m.user_id for m in admins) == ["u2", "u3"]

    def test_owners_of_group(self, members_table):
        Member(group_id="g1", user_id="u1", role="owner",  joined_at="2024-01-01").save()
        Member(group_id="g1", user_id="u2", role="member", joined_at="2024-01-02").save()

        owners, _ = Member.ByRole.query(group_id="g1", role="owner")
        assert [m.user_id for m in owners] == ["u1"]
