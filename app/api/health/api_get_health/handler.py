from datetime import datetime, UTC

from common.awslambda.response_handler import ResponseHandler

ROUTE = ("GET", "/health")


@ResponseHandler.api
def handler(event, context):
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }
