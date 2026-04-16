import uuid
from datetime import datetime, UTC

from common.awslambda.response_handler import ResponseHandler
from common.awslambda.request_util import parse_event

from common.models import User

ROUTE = ("POST", "/users")


@ResponseHandler.api
def handler(event, context):
    body = parse_event(event)

    user = User(
        user_id=str(uuid.uuid4()),
        email=body.get("email", ""),
        name=body.get("name", ""),
        created_at=datetime.now(UTC).isoformat(),
    )
    user.save()
    return 201, user.model_dump()
