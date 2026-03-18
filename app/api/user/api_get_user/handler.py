from common.awslambda.response_handler import ResponseHandler
from common.awslambda.request_util import get_path_params
from common.awslambda.exceptions import NotFoundError

ROUTE = ("GET", "/users/{user_id}")

# TODO: DynamoDB 연동
# import os
# import boto3
# TABLE_NAME = os.environ["TABLE_NAME"]
# table = boto3.resource("dynamodb").Table(TABLE_NAME)


@ResponseHandler.api
def handler(event, context):
    user_id = get_path_params(event).get("user_id")

    # TODO: PynamoDB model로 조회
    # item = table.get_item(Key={"user_id": user_id}).get("Item")
    # if not item:
    #     raise NotFoundError(f"User not found: {user_id}")
    # return item

    return {"user_id": user_id}
