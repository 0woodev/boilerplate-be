# TODO: replace placeholder X-Auth-User header with real JWT bearer auth
"""헤더 기반 인증 스켈레톤.

현재는 `X-Auth-User` 헤더(값=username) 만 읽는 placeholder 인증이다.
실제 토큰/JWT 검증은 미구현 — `require_authenticated_user` 내부만 교체하면 됨.

사용:
    from common.access import require_authenticated_user

    @ResponseHandler.api
    def handler(event, context):
        username = require_authenticated_user(event)
        # 이후 username 사용
"""
import bcrypt

from common.awslambda.exceptions import UnauthorizedError
from common.awslambda.request_util import get_header

AUTH_USER_HEADER = "X-Auth-User"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def require_authenticated_user(event: dict) -> str:
    """요청 유저가 `X-Auth-User` 헤더로 식별되는지 검증.

    Returns:
        username (str)

    Raises:
        UnauthorizedError: 헤더 없음
    """
    username = get_header(event, AUTH_USER_HEADER).strip()
    if not username:
        raise UnauthorizedError(f"{AUTH_USER_HEADER} header is required")
    return username
