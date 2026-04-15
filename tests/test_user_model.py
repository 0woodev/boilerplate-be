from common.models import User
from tests.conftest import create_table

import pytest


USERS_TABLE = "test-local-users"


@pytest.fixture
def users_table(aws):
    create_table(
        USERS_TABLE,
        gsi=[
            {"name": "ByEmail",  "hash_key": "ByEmailPK",  "range_key": "ByEmailSK"},
            {"name": "ByStatus", "hash_key": "ByStatusPK", "range_key": "ByStatusSK"},
        ],
    )


class TestUserCrud:
    def test_save_and_get(self, users_table):
        u = User(
            user_id="u1",
            email="alice@example.com",
            name="Alice",
            created_at="2024-01-15T10:00:00Z",
        )
        u.save()
        got = User.get(user_id="u1")
        assert got is not None
        assert got.email == "alice@example.com"
        assert got.name == "Alice"
        assert got.status == "active"

    def test_update_status(self, users_table):
        User(
            user_id="u1",
            email="alice@example.com",
            created_at="2024-01-15T10:00:00Z",
        ).save()
        User.update_by_key({"status": "suspended"}, user_id="u1")
        assert User.get(user_id="u1").status == "suspended"


class TestUserGsiByEmail:
    def test_find_by_email(self, users_table):
        User(
            user_id="u1",
            email="alice@example.com",
            created_at="2024-01-15T10:00:00Z",
        ).save()
        User(
            user_id="u2",
            email="bob@example.com",
            created_at="2024-01-16T10:00:00Z",
        ).save()

        users, _ = User.ByEmail.query(email="alice@example.com")
        assert len(users) == 1
        assert users[0].user_id == "u1"

    def test_email_not_found(self, users_table):
        users, _ = User.ByEmail.query(email="nobody@example.com")
        assert users == []


class TestUserGsiByStatus:
    def test_list_by_status(self, users_table):
        User(user_id="u1", status="active",    email="a@x.com", created_at="2024-01-01").save()
        User(user_id="u2", status="active",    email="b@x.com", created_at="2024-02-01").save()
        User(user_id="u3", status="suspended", email="c@x.com", created_at="2024-01-15").save()

        actives, _ = User.ByStatus.query(status="active")
        assert sorted(u.user_id for u in actives) == ["u1", "u2"]

    def test_status_and_date_range(self, users_table):
        User(user_id="u1", status="active", email="a@x.com", created_at="2024-01-15").save()
        User(user_id="u2", status="active", email="b@x.com", created_at="2024-06-15").save()
        User(user_id="u3", status="active", email="c@x.com", created_at="2024-12-15").save()

        # "2024-01 ~ 2024-06 사이 가입한 active 유저"
        users, _ = User.ByStatus.query_between(
            status="active",
            start={"created_at": "2024-01-01"},
            end={"created_at": "2024-06-30"},
        )
        assert sorted(u.user_id for u in users) == ["u1", "u2"]
