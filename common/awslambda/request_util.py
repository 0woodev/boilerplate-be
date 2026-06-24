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


def get_header(event: dict, name: str) -> str:
    """대소문자 구분 없이 헤더 값 반환. 없으면 "".

    API Gateway v2는 키를 소문자로 정규화하지만, Flask 로컬 서버는 원본 대소문자를 유지한다.
    양쪽 다 처리.
    """
    headers = event.get("headers") or {}
    lower = name.lower()
    for k, v in headers.items():
        if k.lower() == lower:
            return v or ""
    return ""
