import pytest

from common.models import PatchNote
from tests.conftest import create_table

from scripts.generate_patch_notes import (
    parse_activity,
    activity_id,
    upsert_rows,
    fill_empty_bodies,
    draft_dev_body,
    draft_user_body,
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
            assert pn.user_body == ""
            assert pn.dev_body == ""

    def test_rerun_preserves_both_bodies(self, patch_notes_table):
        rows = parse_activity(ACTIVITY)
        upsert_rows(rows)

        # 한 노트의 두 본문을 수작업으로 채운다.
        target_id = activity_id(
            "2026-06-23", "be", "access.py(bcrypt, X-Auth-User placeholder) 추가",
        )
        pn = PatchNote.get(patch_note_id=target_id)
        pn.user_body = "## 수작업 user"
        pn.dev_body = "## 수작업 dev"
        pn.save()

        # 재실행 → 같은 id 로 매핑, 두 본문 모두 보존되어야 한다.
        upsert_rows(rows)
        again = PatchNote.get(patch_note_id=target_id)
        assert again.user_body == "## 수작업 user"
        assert again.dev_body == "## 수작업 dev"

    def test_rerun_preserves_bodies_independently(self, patch_notes_table):
        # 한 본문만 채워져 있어도 그것만 보존되고 빈 본문은 그대로 빈 채로 둔다.
        rows = parse_activity(ACTIVITY)
        upsert_rows(rows)
        target_id = activity_id("2026-06-22", "fe", "앱셸·헤더인증 스켈레톤")
        pn = PatchNote.get(patch_note_id=target_id)
        pn.dev_body = "kept dev only"
        pn.save()

        upsert_rows(rows)
        again = PatchNote.get(patch_note_id=target_id)
        assert again.dev_body == "kept dev only"
        assert again.user_body == ""

    def test_rerun_updates_title_but_keeps_bodies(self, patch_notes_table):
        row = {"date": "2026-06-23", "scope": "be", "title": "old summary"}
        upsert_rows([row])
        pn_id = activity_id("2026-06-23", "be", "old summary")
        pn = PatchNote.get(patch_note_id=pn_id)
        pn.user_body = "kept user"
        pn.dev_body = "kept dev"
        pn.save()

        # title 자체가 멱등 키의 일부이므로, title 이 바뀌면 새 노트가 된다.
        # → 같은 행 재실행 시(title 동일)에는 갱신 경로를 타고 본문이 보존된다.
        upsert_rows([row])
        again = PatchNote.get(patch_note_id=pn_id)
        assert again.title == "old summary"
        assert again.user_body == "kept user"
        assert again.dev_body == "kept dev"

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
        # system 프롬프트로 dev/user 초안을 구분해 서로 다른 텍스트를 돌려준다.
        text = "## DEV 초안" if "technical audience" in kwargs["system"] else "## USER 초안"

        class _Block:
            pass

        block = _Block()
        block.type = "text"
        block.text = text

        class _Resp:
            content = [block]

        return _Resp()


class _MockClient:
    def __init__(self):
        self.calls = []
        self.messages = _MockMessages(self.calls)


class TestL2FillEmptyBodies:
    def test_fills_both_empty_bodies(self, patch_notes_table):
        rows = parse_activity(ACTIVITY)
        saved = upsert_rows(rows)

        client = _MockClient()
        filled = fill_empty_bodies(saved, client=client, model="claude-sonnet-4-6")

        # 3개 노트 × 2 본문 = 6개 본문이 채워진다 (call 도 6번).
        assert filled == 6
        assert len(client.calls) == 6

        for pn in saved:
            refreshed = PatchNote.get(patch_note_id=pn.patch_note_id)
            assert refreshed.dev_body == "## DEV 초안"
            assert refreshed.user_body == "## USER 초안"

    def test_skips_already_filled_bodies(self, patch_notes_table):
        rows = parse_activity(ACTIVITY)
        saved = upsert_rows(rows)
        # 한 노트의 두 본문을 미리 채워둔다 → 둘 다 건너뛰어야 한다.
        saved[0].user_body = "수작업 user"
        saved[0].dev_body = "수작업 dev"
        saved[0].save()

        client = _MockClient()
        filled = fill_empty_bodies(saved, client=client, model="claude-sonnet-4-6")

        # 남은 2개 노트 × 2 본문 = 4개만 채워진다.
        assert filled == 4
        assert len(client.calls) == 4

        preserved = PatchNote.get(patch_note_id=saved[0].patch_note_id)
        assert preserved.user_body == "수작업 user"
        assert preserved.dev_body == "수작업 dev"

    def test_fills_only_the_empty_one_when_one_present(self, patch_notes_table):
        # 한 본문만 비어 있으면 그것만 채우고 채워진 쪽은 보존한다.
        rows = parse_activity(ACTIVITY)
        saved = upsert_rows(rows)
        note = saved[0]
        note.dev_body = "수작업 dev"   # dev 는 채워짐, user 는 빔
        note.save()

        # 이 노트 하나만 대상으로 호출.
        client = _MockClient()
        filled = fill_empty_bodies([note], client=client, model="claude-sonnet-4-6")

        # user_body 하나만 채워진다.
        assert filled == 1
        assert len(client.calls) == 1
        # USER 프롬프트만 호출됐어야 한다.
        assert "non-technical" in client.calls[0]["system"]

        refreshed = PatchNote.get(patch_note_id=note.patch_note_id)
        assert refreshed.dev_body == "수작업 dev"
        assert refreshed.user_body == "## USER 초안"

    def test_no_network_call_when_all_filled(self, patch_notes_table):
        rows = parse_activity(ACTIVITY)
        saved = upsert_rows(rows)
        for pn in saved:
            pn.user_body = "있음"
            pn.dev_body = "있음"
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
        for draft in (draft_dev_body, draft_user_body):
            client.calls.clear()
            draft(
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
            title=long_title, user_body="", dev_body="", source="activity",
            created_at="x", updated_at="x",
        )
        client = _MockClient()
        draft_dev_body(pn, client=client, model="claude-sonnet-4-6", max_input_chars=100)
        sent = client.calls[0]["messages"][0]["content"]
        # summary 부분이 캡을 넘지 않아야 한다.
        assert "x" * 101 not in sent
