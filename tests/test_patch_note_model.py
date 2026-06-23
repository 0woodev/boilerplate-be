from common.models import PatchNote
from tests.conftest import create_table

import pytest


PATCH_NOTES_TABLE = "test-local-patch-notes"


@pytest.fixture
def patch_notes_table(aws):
    create_table(
        PATCH_NOTES_TABLE,
        gsi=[
            {"name": "ByDate", "hash_key": "ByDatePK", "range_key": "ByDateSK"},
        ],
    )


class TestPatchNoteCrud:
    def test_save_and_get(self, patch_notes_table):
        pn = PatchNote(
            patch_note_id="pn_1",
            date="2026-06-23",
            scope="be",
            title="Add patch notes",
            body="## Body",
            source="manual",
            created_at="2026-06-23T10:00:00+00:00",
            updated_at="2026-06-23T10:00:00+00:00",
        )
        pn.save()
        got = PatchNote.get(patch_note_id="pn_1")
        assert got is not None
        assert got.title == "Add patch notes"
        assert got.scope == "be"
        assert got.body == "## Body"
        assert got.source == "manual"

    def test_roundtrip_excludes_internal_keys(self, patch_notes_table):
        PatchNote(
            patch_note_id="pn_1",
            date="2026-06-23",
            scope="be",
            title="t",
            created_at="2026-06-23T10:00:00+00:00",
            updated_at="2026-06-23T10:00:00+00:00",
        ).save()
        got = PatchNote.get(patch_note_id="pn_1")
        dumped = got.model_dump()
        # GSI/key 컬럼이 모델 필드로 새어들어오지 않아야 한다.
        for internal in ("PK", "SK", "ByDatePK", "ByDateSK"):
            assert internal not in dumped


class TestPatchNoteByDate:
    def test_query_all_in_partition(self, patch_notes_table):
        PatchNote(patch_note_id="pn_1", date="2026-06-20", scope="be",
                  title="a", created_at="x", updated_at="2026-06-20T10:00:00+00:00").save()
        PatchNote(patch_note_id="pn_2", date="2026-06-22", scope="fe",
                  title="b", created_at="x", updated_at="2026-06-22T10:00:00+00:00").save()

        notes, _ = PatchNote.ByDate.query()
        assert {n.patch_note_id for n in notes} == {"pn_1", "pn_2"}

    def test_ascending_sort_by_date_then_updated_at(self, patch_notes_table):
        # 같은 date 의 두 항목은 updated_at 으로 정렬되어야 한다.
        PatchNote(patch_note_id="pn_late", date="2026-06-22", scope="be",
                  title="late", created_at="x", updated_at="2026-06-22T12:00:00+00:00").save()
        PatchNote(patch_note_id="pn_early", date="2026-06-22", scope="be",
                  title="early", created_at="x", updated_at="2026-06-22T09:00:00+00:00").save()
        PatchNote(patch_note_id="pn_old", date="2026-06-20", scope="be",
                  title="old", created_at="x", updated_at="2026-06-20T10:00:00+00:00").save()

        notes, _ = PatchNote.ByDate.query()
        # DynamoDB 는 SK 오름차순 반환: date asc, 동률이면 updated_at asc
        assert [n.patch_note_id for n in notes] == ["pn_old", "pn_early", "pn_late"]
