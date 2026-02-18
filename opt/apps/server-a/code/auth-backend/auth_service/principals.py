from __future__ import annotations

from common_auth.principal import Principal

from auth_service.models import User


def build_principal(user: User, perms: set[str], token: str | None = None) -> Principal:
    return Principal(
        user_id=str(user.id),
        level=user.level,
        status=user.status,
        groups=list(user.groups or []),
        perms=perms,
        token=token,
    )
