from __future__ import annotations

import secrets
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache
from jwt import PyJWKClient
from urllib.parse import quote_plus

STATE_TTL = 300


def _state_key(state: str) -> str:
    return f"oauth-state:{state}"


def create_state(provider: str, redirect: str | None) -> str:
    state = secrets.token_urlsafe(16)
    cache.set(_state_key(state), {"provider": provider, "redirect": redirect}, timeout=STATE_TTL)
    return state


def consume_state(state: str) -> dict[str, Any]:
    data = cache.get(_state_key(state))
    if not data:
        raise ValueError("invalid_state")
    cache.delete(_state_key(state))
    return data


def _fetch_json(url: str, data: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(url, data=data, timeout=10)
    response.raise_for_status()
    return response.json()


def _jwks_decode(token: str, jwks_url: str, audience: str, issuer: str) -> dict[str, Any]:
    jwk_client = PyJWKClient(jwks_url)
    signing_key = jwk_client.get_signing_key_from_jwt(token)
    import jwt

    return jwt.decode(token, signing_key.key, algorithms=["RS256"], audience=audience, issuer=issuer)


def google_authorize_url(redirect_uri: str, state: str) -> str:
    scope = "openid email profile"
    return (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={quote_plus(settings.GOOGLE_CLIENT_ID)}&"
        f"redirect_uri={quote_plus(redirect_uri)}&response_type=code&scope={quote_plus(scope)}&state={quote_plus(state)}"
    )


def google_tokens(code: str, redirect_uri: str) -> dict[str, Any]:
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    return _fetch_json("https://oauth2.googleapis.com/token", data)


def google_identity(id_token: str) -> dict[str, Any]:
    payload = _jwks_decode(
        id_token,
        "https://www.googleapis.com/oauth2/v3/certs",
        settings.GOOGLE_CLIENT_ID,
        "https://accounts.google.com",
    )
    return {
        "provider": "google",
        "providerUserId": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "email_verified": payload.get("email_verified", False),
    }


def microsoft_authorize_url(redirect_uri: str, state: str) -> str:
    scope = "openid email profile User.Read"
    tenant = settings.MS_TENANT or "common"
    return (
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?"
        f"client_id={quote_plus(settings.MS_CLIENT_ID)}&response_type=code&redirect_uri={quote_plus(redirect_uri)}"
        f"&response_mode=query&scope={quote_plus(scope)}&state={quote_plus(state)}"
    )


def microsoft_tokens(code: str, redirect_uri: str) -> dict[str, Any]:
    tenant = settings.MS_TENANT or "common"
    data = {
        "client_id": settings.MS_CLIENT_ID,
        "client_secret": settings.MS_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "scope": "openid email profile User.Read",
    }
    return _fetch_json(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data)


def microsoft_identity(id_token: str) -> dict[str, Any]:
    tenant = settings.MS_TENANT or "common"
    payload = _jwks_decode(
        id_token,
        f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
        settings.MS_CLIENT_ID,
        f"https://login.microsoftonline.com/{tenant}/v2.0",
    )
    email = payload.get("email") or payload.get("preferred_username")
    return {
        "provider": "microsoft",
        "providerUserId": payload.get("oid"),
        "email": email,
        "name": payload.get("name"),
        "email_verified": True,
    }
