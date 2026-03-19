from common.awslambda.response_handler import ResponseHandler
from common.awslambda.request_util import parse_event

ROUTE = ("GET", "/users")


@ResponseHandler.api
def handler(event, context):
    return {"message": "ok", "users": [], "total": 0, "page": 1}
