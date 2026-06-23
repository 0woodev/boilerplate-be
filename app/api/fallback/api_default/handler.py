"""Catch-all handler for unmatched API Gateway routes.

API Gateway HTTP v2 returns its own response (without CORS headers) for
unmatched routes.  This $default route catches them and returns a proper
404 with CORS headers applied by the gateway's cors_configuration.

OPTIONS preflight은 API Gateway가 자동 CORS 응답을 보내야 하지만,
$default 라우트가 존재하면 그 자동 처리가 비활성화되고 모든 OPTIONS가
여기로 라우팅된다. 그래서 OPTIONS는 204로 즉시 반환해 preflight를
성공시킨다 (CORS 헤더는 gateway의 cors_configuration이 부착).
"""
from common.awslambda.response_handler import ResponseHandler
from common.awslambda.exceptions import NotFoundError

ROUTE = ("$default", "$default")


@ResponseHandler.api
def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")
    if method == "OPTIONS":
        return None
    raise NotFoundError(f"No route: {method} {path}")
