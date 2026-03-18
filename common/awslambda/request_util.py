import json


def parse_event(event: dict) -> dict:
    """API GW v2 event body를 dict으로 파싱"""
    body = event.get("body") or "{}"
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}
    return body


def get_path_params(event: dict) -> dict:
    return event.get("pathParameters") or {}


def get_query_params(event: dict) -> dict:
    return event.get("queryStringParameters") or {}
