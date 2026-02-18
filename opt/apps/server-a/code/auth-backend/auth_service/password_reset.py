from __future__ import annotations

import secrets

from datetime import timedelta

from django.conf import settings

from auth_service.models import PasswordResetToken, User
from auth_service.utils import hash_token, utcnow


class ResetTokenError(Exception):
    pass


def issue_reset_token(user: User) -> str:
    plain = secrets.token_urlsafe(32)
    token = PasswordResetToken(
        tokenHash=hash_token(plain),
        userId=user,
        expiresAt=utcnow() + timedelta(minutes=settings.PASSWORD_RESET_EXP_MINUTES),
    )
    token.save()
    return plain


def consume_reset_token(plain_token: str) -> User:
    token_hash = hash_token(plain_token)
    token = PasswordResetToken.objects(tokenHash=token_hash, used=False).first()
    if token is None:
        raise ResetTokenError("Invalid or expired token")
    if token.expiresAt < utcnow():
        raise ResetTokenError("Token expired")
    token.mark_used()
    return token.userId