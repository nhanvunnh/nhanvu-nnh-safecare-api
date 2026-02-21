import jwt
from django.conf import settings

from gnh_gateway.constants import has_scope
from gnh_gateway.models import COL_API_TOKEN, utcnow
from gnh_gateway.mongo import get_collection


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

    doc = get_collection(COL_API_TOKEN).find_one({"token": token, "isActive": True})
    if not doc:
        return False

    expires_at = doc.get("expiresAt")
    if expires_at and expires_at < utcnow():
        return False

    return has_scope(doc.get("scope", ""), required_scope)


def require_auth(request, required_scope: str = "read"):
    from gnh_gateway.utils import get_param

    api_token = get_param(request, "api_token", "")
    if verify_api_token(api_token, required_scope=required_scope):
        return

    user_token = get_param(request, "token", "")
    payload = decode_user_token(user_token)
    if payload is not None:
        return

    raise Exception("Unauthorized")
