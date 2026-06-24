from typing import ClassVar

from common.dynamo import DynamoModel, GSI


class PatchNote(DynamoModel):
    table_name:  ClassVar[str] = "{project_name}-{stage}-patch-notes"
    pk_attr:     ClassVar[str] = "PK"
    sk_attr:     ClassVar[str] = "SK"
    pk_template: ClassVar[str] = "PATCH_NOTE_ID@{patch_note_id}"
    sk_template: ClassVar[str] = "TYPE@patch_note"

    patch_note_id: str = ""
    date:          str = ""              # "YYYY-MM-DD"
    scope:         str = ""              # be | fe | infra | root | docs
    title:         str = ""
    user_body:     str = ""              # Markdown, 사용자 친화 본문, "" 가능
    dev_body:      str = ""              # Markdown, 기술 본문, "" 가능
    source:        str = "manual"        # activity | manual
    created_at:    str = ""
    updated_at:    str = ""

    # 전체 목록을 date 정렬로 조회하기 위한 GSI.
    # hash 는 상수("patch_note") → 모든 항목이 단일 파티션에 모인다.
    # range 는 date#updated_at → DynamoDB 가 date 우선, 동률이면 updated_at 으로 정렬.
    # (DynamoDB 는 오름차순 반환 → 핸들러에서 reverse 하여 내림차순 제공)
    class ByDate(GSI):
        pk_attr:     ClassVar[str] = "ByDatePK"
        sk_attr:     ClassVar[str] = "ByDateSK"
        pk_template: ClassVar[str] = "TYPE@patch_note"
        sk_template: ClassVar[str] = "DATE@{date}#{updated_at}"
