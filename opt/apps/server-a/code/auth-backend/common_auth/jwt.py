from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from common_auth import errors

ALGORITHM = "HS256"


def encode_jwt(
    payload: dict[str, Any],
    secret: str,
    expires_minutes: int,
    issuer: str,
    audience: str,
    algorithm: str = ALGORITHM,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)
    token_payload = {
        **payload,
        "iss": issuer,
        "aud": audience,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(token_payload, secret, algorithm=algorithm)


def verify_jwt(
    token: str,
    secret: str,
    issuer: str,
    audience: str,
    algorithms: list[str] | None = None,
) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=algorithms or [ALGORITHM],
            issuer=issuer,
            audience=audience,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:  # pragma: no cover - PyJWT ensures behavior
        raise errors.ExpiredTokenError() from exc
    except jwt.InvalidTokenError as exc:  # pragma: no cover - PyJWT ensures behavior
        raise errors.InvalidTokenError(str(exc)) from exc
