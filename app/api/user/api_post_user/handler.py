from common.awslambda.response_handler import ResponseHandler
from common.awslambda.request_util import parse_event

ROUTE = ("POST", "/users")

# TODO: DynamoDB 연동
# import uuid
# import os
# import boto3
# TABLE_NAME = os.environ["TABLE_NAME"]
# table = boto3.resource("dynamodb").Table(TABLE_NAME)


@ResponseHandler.api
def handler(event, context):
    body = parse_event(event)

    # TODO: PynamoDB model로 저장 후 생성된 리소스 반환
    # user_id = str(uuid.uuid4())
    # user = User(user_id=user_id, **body)
    # user.save()
    # return 201, user.to_dict()

    return 201, {"user_id": "todo", **body}
