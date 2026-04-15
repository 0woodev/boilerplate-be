from common.dynamo.keys import placeholders, render_full, render_partial

import pytest


class TestPlaceholders:
    def test_none(self):
        assert placeholders("TYPE@profile") == []

    def test_single(self):
        assert placeholders("USER_ID@{user_id}") == ["user_id"]

    def test_multiple_in_order(self):
        assert placeholders("DATE@{date}#TYPE@{record_type}") == ["date", "record_type"]


class TestRenderFull:
    def test_no_placeholders_returns_as_is(self):
        assert render_full("TYPE@profile", {}) == "TYPE@profile"

    def test_all_fields_present(self):
        got = render_full("USER_ID@{user_id}", {"user_id": "u1"})
        assert got == "USER_ID@u1"

    def test_composite(self):
        got = render_full(
            "DATE@{date}#TYPE@{record_type}",
            {"date": "2024-01-15", "record_type": "workout"},
        )
        assert got == "DATE@2024-01-15#TYPE@workout"

    def test_missing_field_raises(self):
        with pytest.raises(ValueError, match="missing required fields"):
            render_full("USER_ID@{user_id}", {})

    def test_empty_field_raises(self):
        with pytest.raises(ValueError, match="missing required fields"):
            render_full("USER_ID@{user_id}", {"user_id": ""})

    def test_none_field_raises(self):
        with pytest.raises(ValueError, match="missing required fields"):
            render_full("USER_ID@{user_id}", {"user_id": None})


class TestRenderPartial:
    def test_empty_template(self):
        assert render_partial("", {}) == ("", True)

    def test_no_placeholders(self):
        assert render_partial("TYPE@profile", {}) == ("TYPE@profile", True)

    def test_all_present_complete(self):
        got, done = render_partial(
            "DATE@{date}#TYPE@{record_type}",
            {"date": "2024-01-15", "record_type": "workout"},
        )
        assert got == "DATE@2024-01-15#TYPE@workout"
        assert done is True

    def test_first_missing_stops(self):
        # date provided, record_type missing
        got, done = render_partial(
            "DATE@{date}#TYPE@{record_type}",
            {"date": "2024-01-15"},
        )
        # includes literal "#TYPE@" that comes BEFORE {record_type}
        assert got == "DATE@2024-01-15#TYPE@"
        assert done is False

    def test_first_field_missing(self):
        got, done = render_partial(
            "DATE@{date}#TYPE@{record_type}",
            {"record_type": "workout"},
        )
        # stops at {date} — nothing useful to render
        assert got == "DATE@"
        assert done is False

    def test_empty_value_treated_as_missing(self):
        got, done = render_partial("DATE@{date}", {"date": ""})
        assert got == "DATE@"
        assert done is False
