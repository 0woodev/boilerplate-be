from common.awslambda.response_handler import ResponseHandler
from common.awslambda.request_util import get_path_params
from common.awslambda.exceptions import NotFoundError

from app.api.user.model import User

ROUTE = ("GET", "/users/{user_id}")


@ResponseHandler.api
def handler(event, context):
    user_id = get_path_params(event).get("user_id")

    user = User.get(user_id=user_id)
    if not user:
        raise NotFoundError(f"User not found: {user_id}")

    return user.model_dump()
