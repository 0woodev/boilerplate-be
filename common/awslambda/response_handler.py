import json
import logging
import functools
import uuid
from typing import Any

from common.awslambda.exceptions import HttpError

logger = logging.getLogger(__name__)

_HEADERS = {"Content-Type": "application/json"}


def _response(status_code: int, body: Any) -> dict:
    return {
        "statusCode": status_code,
        "headers": _HEADERS,
        "body": json.dumps(body, ensure_ascii=False) if body is not None else "",
    }


class ResponseHandler:
    @staticmethod
    def api(func):
        """
        Lambda 핸들러 데코레이터.

        핸들러 반환값 규칙:
          - dict / list     → 200 OK
          - (int, any)      → int 상태코드 + body  ex) return 201, {"user_id": ...}
          - None            → 204 No Content
          - raise HttpError → 해당 status_code + {"error": message}
          - raise Exception → 500 + {"error": "Internal server error"}
        """

        @functools.wraps(func)
        def wrapper(event, context):
            try:
                result = func(event, context)

                if result is None:
                    return _response(204, None)

                if isinstance(result, tuple):
                    status_code, data = result
                    return _response(status_code, data)

                return _response(200, result)

            except HttpError as e:
                error_id = str(uuid.uuid4())
                logger.error("[%s] %s: %s", error_id, type(e).__name__, e.message)
                return _response(e.status_code, {"error": e.message, "error_id": error_id})

            except Exception:
                error_id = str(uuid.uuid4())
                logger.exception("[%s] Unhandled exception in %s", error_id, func.__qualname__)
                return _response(500, {"error": "Internal server error", "error_id": error_id})

        return wrapper
