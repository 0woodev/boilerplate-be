class HttpError(Exception):
    status_code: int = 500

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class BadRequestError(HttpError):
    status_code = 400


class UnauthorizedError(HttpError):
    status_code = 401


class ForbiddenError(HttpError):
    status_code = 403


class NotFoundError(HttpError):
    status_code = 404


class ConflictError(HttpError):
    status_code = 409
