from datetime import datetime, UTC

from common.awslambda.response_handler import ResponseHandler
from common.awslambda.request_util import parse_event
from common.awslambda.exceptions import BadRequestError
from common.access import require_authenticated_user
from common.ids import generate_id

from common.models import PatchNote

ROUTE = ("POST", "/patch-notes")


@ResponseHandler.api
def handler(event, context):
    require_authenticated_user(event)
    body = parse_event(event)

    date = body.get("date", "")
    scope = body.get("scope", "")
    title = body.get("title", "")
    if not date or not scope or not title:
        raise BadRequestError("date, scope, title are required")

    now = datetime.now(UTC).isoformat()
    pn = PatchNote(
        patch_note_id=generate_id("pn"),
        date=date,
        scope=scope,
        title=title,
        body=body.get("body", ""),
        source="manual",
        created_at=now,
        updated_at=now,
    )
    pn.save()
    return 201, pn.model_dump()
