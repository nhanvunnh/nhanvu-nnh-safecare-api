import jwt
import requests
from django.conf import settings

from sheet_sync_gateway.models import COL_API_TOKENS
from sheet_sync_gateway.mongo import get_collection
from sheet_sync_gateway.utils import get_param, has_scope, utcnow


def decode_user_token(token: str):
    if not token:
        return None
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except Exception:
        return None


def verify_api_token(token: str, required_scope: str = "read") -> bool:
    if not token:
        return False

    # Prefer centralized token verification from auth service.
    if settings.AUTH_API_VERIFY_ENABLED:
        try:
            headers = {}
            if settings.AUTH_API_VERIFY_HOST:
                headers["Host"] = settings.AUTH_API_VERIFY_HOST
            resp = requests.post(
                settings.AUTH_API_VERIFY_URL,
                json={"token": token, "requiredScope": required_scope},
                headers=headers or None,
                timeout=max(1, settings.AUTH_API_VERIFY_TIMEOUT),
            )
            if resp.status_code < 500:
                body = resp.json()
                return bool(body.get("active", False))
        except Exception:
            pass

    if not settings.AUTH_API_VERIFY_FALLBACK_LOCAL:
        return False

    doc = get_collection(COL_API_TOKENS).find_one({"token": token, "isActive": True})
    if not doc:
        return False

    expires_at = doc.get("expiresAt")
    if expires_at and expires_at < utcnow():
        return False

    return has_scope(doc.get("scope", ""), required_scope)


def require_auth(request, required_scope: str = "read"):
    api_token = get_param(request, "api_token", "")
    if verify_api_token(api_token, required_scope=required_scope):
        return

    service_token = get_param(request, "service_token", "")
    if settings.INTERNAL_SERVICE_TOKEN and service_token == settings.INTERNAL_SERVICE_TOKEN:
        return

    user_token = get_param(request, "token", "")
    payload = decode_user_token(user_token)
    if payload is not None:
        return

    raise Exception("Unauthorized")
