import pytest

from common.models import PatchNote
from tests.conftest import create_table

from scripts.generate_patch_notes import (
    parse_activity,
    activity_id,
    upsert_rows,
    fill_empty_bodies,
    draft_body,
)


PATCH_NOTES_TABLE = "test-local-patch-notes"


@pytest.fixture
def patch_notes_table(aws):
    create_table(
        PATCH_NOTES_TABLE,
        gsi=[
            {"name": "ByDate", "hash_key": "ByDatePK", "range_key": "ByDateSK"},
        ],
    )


ACTIVITY = """# 활동 로그

| 날짜 | scope | 요약 |
|---|---|---|
| 2026-06-23 | be | access.py(bcrypt, X-Auth-User placeholder) 추가 |
| 2026-06-22 | fe | 앱셸·헤더인증 스켈레톤 |
| not-a-date | be | 무시되어야 함 |
| 2026-06-21 | nope | 잘못된 scope → 무시 |
| 2026-06-20 | docs | db-operations 문서 |
"""


# ── 파싱 ──────────────────────────────────────────────────────
class TestParseActivity:
    def test_parses_valid_rows_only(self):
        rows = parse_activity(ACTIVITY)
        assert len(rows) == 3
        assert rows[0] == {
            "date": "2026-06-23", "scope": "be",
            "title": "access.py(bcrypt, X-Auth-User placeholder) 추가",
        }
        scopes = {r["scope"] for r in rows}
        assert scopes == {"be", "fe", "docs"}

    def test_skips_header_and_separator(self):
        rows = parse_activity(ACTIVITY)
        assert all(r["date"] != "날짜" for r in rows)

    def test_activity_id_is_deterministic(self):
        a = activity_id("2026-06-23", "be", "x")
        b = activity_id("2026-06-23", "be", "x")
        assert a == b == activity_id("2026-06-23", "be", "x")
        assert a.startswith("pn_act_")
        assert activity_id("2026-06-23", "be", "y") != a


# ── L1 멱등 업서트 ────────────────────────────────────────────
class TestUpsertIdempotency:
    def test_creates_activity_notes(self, patch_notes_table):
        rows = parse_activity(ACTIVITY)
        saved = upsert_rows(rows)
        assert len(saved) == 3
        for pn in saved:
            assert pn.source == "activity"
            assert pn.patch_note_id.startswith("pn_act_")
            assert pn.body == ""

    def test_rerun_preserves_body(self, patch_notes_table):
        rows = parse_activity(ACTIVITY)
        upsert_rows(rows)

        # 한 노트의 body 를 수작업으로 채운다.
        target_id = activity_id(
            "2026-06-23", "be", "access.py(bcrypt, X-Auth-User placeholder) 추가",
        )
        pn = PatchNote.get(patch_note_id=target_id)
        pn.body = "## 수작업 body"
        pn.save()

        # 재실행 → 같은 id 로 매핑, body 보존되어야 한다.
        upsert_rows(rows)
        again = PatchNote.get(patch_note_id=target_id)
        assert again.body == "## 수작업 body"

    def test_rerun_updates_title_but_keeps_body(self, patch_notes_table):
        row = {"date": "2026-06-23", "scope": "be", "title": "old summary"}
        upsert_rows([row])
        pn_id = activity_id("2026-06-23", "be", "old summary")
        pn = PatchNote.get(patch_note_id=pn_id)
        pn.body = "kept body"
        pn.save()

        # title 자체가 멱등 키의 일부이므로, title 이 바뀌면 새 노트가 된다.
        # → 같은 행 재실행 시(title 동일)에는 갱신 경로를 타고 body 가 보존된다.
        upsert_rows([row])
        again = PatchNote.get(patch_note_id=pn_id)
        assert again.title == "old summary"
        assert again.body == "kept body"

    def test_rerun_no_duplicates(self, patch_notes_table):
        rows = parse_activity(ACTIVITY)
        upsert_rows(rows)
        upsert_rows(rows)
        notes, _ = PatchNote.ByDate.query()
        assert len(notes) == 3


# ── L2 LLM 초안 (mock client) ─────────────────────────────────
class _MockMessages:
    def __init__(self, recorder):
        self._recorder = recorder

    def create(self, **kwargs):
        self._recorder.append(kwargs)

        class _Block:
            type = "text"
            text = "## LLM 초안\n- 자동 생성"

        class _Resp:
            content = [_Block()]

        return _Resp()


class _MockClient:
    def __init__(self):
        self.calls = []
        self.messages = _MockMessages(self.calls)


class TestL2FillEmptyBodies:
    def test_fills_only_empty_bodies(self, patch_notes_table):
        rows = parse_activity(ACTIVITY)
        saved = upsert_rows(rows)
        # 한 노트만 body 를 미리 채워둔다 → 이건 건너뛰어야 한다.
        saved[0].body = "수작업 body"
        saved[0].save()

        client = _MockClient()
        filled = fill_empty_bodies(saved, client=client, model="claude-sonnet-4-6")

        # 3개 중 1개는 이미 body 가 있으므로 2개만 채워진다.
        assert filled == 2
        assert len(client.calls) == 2

        # 이미 채워진 노트는 보존.
        preserved = PatchNote.get(patch_note_id=saved[0].patch_note_id)
        assert preserved.body == "수작업 body"

        # 빈 노트들은 LLM 초안으로 채워짐.
        for pn in saved[1:]:
            refreshed = PatchNote.get(patch_note_id=pn.patch_note_id)
            assert refreshed.body == "## LLM 초안\n- 자동 생성"

    def test_no_network_call_when_all_filled(self, patch_notes_table):
        rows = parse_activity(ACTIVITY)
        saved = upsert_rows(rows)
        for pn in saved:
            pn.body = "있음"
            pn.save()
        client = _MockClient()
        filled = fill_empty_bodies(saved, client=client, model="claude-sonnet-4-6")
        assert filled == 0
        assert client.calls == []

    def test_external_input_not_in_system_prompt(self, patch_notes_table):
        # 프롬프트 인젝션 방어: ACTIVITY 텍스트는 user role 로만 전달.
        rows = parse_activity(ACTIVITY)
        saved = upsert_rows(rows)
        client = _MockClient()
        draft_body(
            saved[0], client=client, model="claude-sonnet-4-6", max_input_chars=4000,
        )
        call = client.calls[0]
        assert saved[0].title not in call["system"]
        assert saved[0].title in call["messages"][0]["content"]
        assert call["messages"][0]["role"] == "user"

    def test_input_length_capped(self, patch_notes_table):
        long_title = "x" * 10000
        pn = PatchNote(
            patch_note_id="pn_long", date="2026-06-23", scope="be",
            title=long_title, body="", source="activity",
            created_at="x", updated_at="x",
        )
        client = _MockClient()
        draft_body(pn, client=client, model="claude-sonnet-4-6", max_input_chars=100)
        sent = client.calls[0]["messages"][0]["content"]
        # summary 부분이 캡을 넘지 않아야 한다.
        assert "x" * 101 not in sent
