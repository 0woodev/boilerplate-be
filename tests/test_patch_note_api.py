import json

import pytest

from common.models import PatchNote
from tests.conftest import create_table

from app.api.patch_note.api_get_patch_notes.handler import handler as get_patch_notes
from app.api.patch_note.api_post_patch_note.handler import handler as post_patch_note
from app.api.patch_note.api_patch_patch_note.handler import handler as patch_patch_note
from app.api.patch_note.api_delete_patch_note.handler import handler as delete_patch_note


PATCH_NOTES_TABLE = "test-local-patch-notes"


@pytest.fixture
def patch_notes_table(aws):
    create_table(
        PATCH_NOTES_TABLE,
        gsi=[
            {"name": "ByDate", "hash_key": "ByDatePK", "range_key": "ByDateSK"},
        ],
    )


def _event(*, body=None, path_params=None, auth=True):
    event = {"headers": {}}
    if auth:
        event["headers"]["X-Auth-User"] = "tester"
    if body is not None:
        event["body"] = json.dumps(body)
    if path_params is not None:
        event["pathParameters"] = path_params
    return event


def _body(resp):
    return json.loads(resp["body"])


# ── GET (public) ──────────────────────────────────────────────
class TestGetPatchNotes:
    def test_public_no_auth_required(self, patch_notes_table):
        resp = get_patch_notes(_event(auth=False), None)
        assert resp["statusCode"] == 200
        assert _body(resp) == {"patch_notes": []}

    def test_sorted_date_desc_then_updated_at_desc(self, patch_notes_table):
        PatchNote(patch_note_id="pn_old", date="2026-06-20", scope="be",
                  title="old", created_at="x", updated_at="2026-06-20T10:00:00+00:00").save()
        PatchNote(patch_note_id="pn_new_early", date="2026-06-22", scope="be",
                  title="ne", created_at="x", updated_at="2026-06-22T09:00:00+00:00").save()
        PatchNote(patch_note_id="pn_new_late", date="2026-06-22", scope="be",
                  title="nl", created_at="x", updated_at="2026-06-22T12:00:00+00:00").save()

        resp = get_patch_notes(_event(auth=False), None)
        ids = [n["patch_note_id"] for n in _body(resp)["patch_notes"]]
        # date 내림차순, 동일 date 면 updated_at 내림차순
        assert ids == ["pn_new_late", "pn_new_early", "pn_old"]


# ── POST (auth, source=manual) ────────────────────────────────
class TestPostPatchNote:
    def test_create_manual(self, patch_notes_table):
        resp = post_patch_note(
            _event(body={"date": "2026-06-23", "scope": "be", "title": "T", "body": "B"}),
            None,
        )
        assert resp["statusCode"] == 201
        data = _body(resp)
        assert data["source"] == "manual"
        assert data["patch_note_id"].startswith("pn_")
        assert data["created_at"] and data["updated_at"]

        stored = PatchNote.get(patch_note_id=data["patch_note_id"])
        assert stored.title == "T"
        assert stored.body == "B"

    def test_body_optional(self, patch_notes_table):
        resp = post_patch_note(
            _event(body={"date": "2026-06-23", "scope": "fe", "title": "T"}),
            None,
        )
        assert resp["statusCode"] == 201
        assert _body(resp)["body"] == ""

    def test_requires_auth(self, patch_notes_table):
        resp = post_patch_note(
            _event(body={"date": "2026-06-23", "scope": "be", "title": "T"}, auth=False),
            None,
        )
        assert resp["statusCode"] == 401

    def test_missing_fields_400(self, patch_notes_table):
        resp = post_patch_note(_event(body={"scope": "be"}), None)
        assert resp["statusCode"] == 400


# ── PATCH (auth, title+body editable) ─────────────────────────
class TestPatchPatchNote:
    def _seed(self):
        PatchNote(
            patch_note_id="pn_1", date="2026-06-23", scope="be",
            title="old title", body="old body", source="manual",
            created_at="2026-06-23T10:00:00+00:00",
            updated_at="2026-06-23T10:00:00+00:00",
        ).save()

    def test_edit_title_and_body(self, patch_notes_table):
        self._seed()
        resp = patch_patch_note(
            _event(body={"title": "new title", "body": "new body"},
                   path_params={"patch_note_id": "pn_1"}),
            None,
        )
        assert resp["statusCode"] == 200
        data = _body(resp)
        assert data["title"] == "new title"
        assert data["body"] == "new body"

        stored = PatchNote.get(patch_note_id="pn_1")
        assert stored.title == "new title"
        assert stored.body == "new body"

    def test_partial_edit_title_only(self, patch_notes_table):
        self._seed()
        resp = patch_patch_note(
            _event(body={"title": "only title"},
                   path_params={"patch_note_id": "pn_1"}),
            None,
        )
        assert resp["statusCode"] == 200
        assert _body(resp)["body"] == "old body"

    def test_not_found_404(self, patch_notes_table):
        resp = patch_patch_note(
            _event(body={"title": "x"}, path_params={"patch_note_id": "nope"}),
            None,
        )
        assert resp["statusCode"] == 404

    def test_requires_auth(self, patch_notes_table):
        self._seed()
        resp = patch_patch_note(
            _event(body={"title": "x"}, path_params={"patch_note_id": "pn_1"}, auth=False),
            None,
        )
        assert resp["statusCode"] == 401

    def test_updated_at_keeps_gsi_sortable(self, patch_notes_table):
        # PATCH 로 updated_at 이 바뀌어도 GSI 정렬이 일관되게 유지되어야 한다.
        PatchNote(patch_note_id="pn_a", date="2026-06-22", scope="be", title="a",
                  created_at="x", updated_at="2026-06-22T09:00:00+00:00").save()
        PatchNote(patch_note_id="pn_b", date="2026-06-22", scope="be", title="b",
                  created_at="x", updated_at="2026-06-22T10:00:00+00:00").save()
        # pn_a 를 수정 → updated_at 이 가장 늦어짐 → 목록 맨 앞이어야 한다.
        patch_patch_note(
            _event(body={"title": "a2"}, path_params={"patch_note_id": "pn_a"}),
            None,
        )
        resp = get_patch_notes(_event(auth=False), None)
        ids = [n["patch_note_id"] for n in _body(resp)["patch_notes"]]
        assert ids[0] == "pn_a"


# ── DELETE (auth, 204) ────────────────────────────────────────
class TestDeletePatchNote:
    def test_delete(self, patch_notes_table):
        PatchNote(patch_note_id="pn_1", date="2026-06-23", scope="be", title="t",
                  created_at="x", updated_at="x").save()
        resp = delete_patch_note(_event(path_params={"patch_note_id": "pn_1"}), None)
        assert resp["statusCode"] == 204
        assert PatchNote.get(patch_note_id="pn_1") is None

    def test_requires_auth(self, patch_notes_table):
        resp = delete_patch_note(
            _event(path_params={"patch_note_id": "pn_1"}, auth=False), None,
        )
        assert resp["statusCode"] == 401
