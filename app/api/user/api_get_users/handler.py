from common.awslambda.response_handler import ResponseHandler
from common.awslambda.request_util import get_query_params

from app.api.user.model import User

ROUTE = ("GET", "/users")


@ResponseHandler.api
def handler(event, context):
    params = get_query_params(event)
    limit = int(params.get("limit", 20))
    cursor = params.get("cursor")

    users, next_cursor = User.scan(limit=limit, cursor=cursor)
    return {
        "users": [u.model_dump() for u in users],
        "next_cursor": next_cursor,
    }
