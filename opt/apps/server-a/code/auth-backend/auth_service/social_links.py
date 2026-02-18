from __future__ import annotations

import secrets

from auth_service import services
from auth_service.models import User, UserSocialLink


def upsert_social_user(provider: str, provider_user_id: str, email: str | None, name: str | None, email_verified: bool) -> User:
    link = UserSocialLink.objects(provider=provider, providerUserId=provider_user_id).first()
    if link:
        return link.userId
    user = None
    if email:
        user = User.objects(email=email).first()
    if not user:
        random_password = secrets.token_urlsafe(16)
        user = services.create_user(
            email=email,
            phone=None,
            full_name=name or email or "Social User",
            password=random_password,
            verified_email=email_verified,
        )
    if email_verified:
        user.verifiedEmail = True
        user.save()
    link = UserSocialLink(userId=user, provider=provider, providerUserId=provider_user_id, email=email)
    link.save()
    return user
