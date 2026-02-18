from __future__ import annotations

from http import HTTPStatus


class AuthError(Exception):
    def __init__(self, code: str, message: str, status: HTTPStatus = HTTPStatus.UNAUTHORIZED):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class InvalidTokenError(AuthError):
    def __init__(self, message: str = "Invalid token"):
        super().__init__("invalid_token", message)


class ExpiredTokenError(AuthError):
    def __init__(self, message: str = "Token expired"):
        super().__init__("expired_token", message)


class MissingTokenError(AuthError):
    def __init__(self, message: str = "Token missing"):
        super().__init__("missing_token", message)


class InactiveUserError(AuthError):
    def __init__(self, message: str = "User inactive"):
        super().__init__("inactive_user", message)
