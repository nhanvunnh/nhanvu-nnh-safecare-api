from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from common_auth import errors as auth_errors, jwt as jwt_utils

from auth_service.constants import STATUS_ACTIVE
from auth_service.models import User
from auth_service.principals import build_principal
from auth_service.rbac import get_user_permissions


class JWTOrCookieAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        token = self._extract_token(request)
        if not token:
            return None
        try:
            payload = jwt_utils.verify_jwt(
                token,
                secret=settings.JWT_SECRET,
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE,
            )
        except auth_errors.AuthError as exc:
            raise AuthenticationFailed(str(exc)) from exc
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationFailed("Invalid token subject")
        user = User.objects(id=user_id).first()
        if not user:
            raise AuthenticationFailed("User not found")
        if user.status != STATUS_ACTIVE:
            raise AuthenticationFailed("User inactive")
        perms = get_user_permissions(user)
        principal = build_principal(user, perms, token)
        request.principal = principal
        return principal, token

    def _extract_token(self, request) -> str | None:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith(f"{self.keyword} "):
            return auth_header.split(" ", 1)[1].strip()
        cookie_token = request.COOKIES.get(settings.COOKIE_NAME)
        if cookie_token:
            return cookie_token.strip()
        return None
