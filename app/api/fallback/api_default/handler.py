"""Catch-all handler for unmatched API Gateway routes.

API Gateway HTTP v2 returns its own response (without CORS headers) for
unmatched routes.  This $default route catches them and returns a proper
404 with CORS headers applied by the gateway's cors_configuration.
"""
from common.awslambda.response_handler import ResponseHandler
from common.awslambda.exceptions import NotFoundError

ROUTE = ("$default", "$default")


@ResponseHandler.api
def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")
    raise NotFoundError(f"No route: {method} {path}")
