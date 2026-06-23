from datetime import datetime, UTC

from common.awslambda.response_handler import ResponseHandler
from common.awslambda.request_util import parse_event, get_path_params
from common.awslambda.exceptions import NotFoundError
from common.access import require_authenticated_user

from common.models import PatchNote

ROUTE = ("PATCH", "/patch-notes/{patch_note_id}")


@ResponseHandler.api
def handler(event, context):
    require_authenticated_user(event)
    patch_note_id = get_path_params(event).get("patch_note_id")
    body = parse_event(event)

    pn = PatchNote.get(patch_note_id=patch_note_id)
    if not pn:
        raise NotFoundError(f"PatchNote not found: {patch_note_id}")

    if "title" in body:
        pn.title = body["title"]
    if "body" in body:
        pn.body = body["body"]
    pn.updated_at = datetime.now(UTC).isoformat()

    # updated_at 이 GSI SK 에 포함되므로 전체 항목을 재저장해 GSI 컬럼까지 갱신.
    pn.save()
    return pn.model_dump()
