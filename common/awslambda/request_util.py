import json


def parse_event(event: dict) -> dict:
    """API GW v2 event body를 dict으로 파싱"""
    body = event.get("body") or "{}"
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            # TODO: return {} 대신 BadRequestError("Invalid JSON body") raise로 변경
            #   현재는 파싱 실패 시 빈 dict 반환 → 에러 원인 추적 불가
            #   from common.awslambda.exceptions import BadRequestError 임포트 후 교체
            return {}
    return body


def get_path_params(event: dict) -> dict:
    return event.get("pathParameters") or {}


def get_query_params(event: dict) -> dict:
    return event.get("queryStringParameters") or {}
