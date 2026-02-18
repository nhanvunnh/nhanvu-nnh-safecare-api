from __future__ import annotations

from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import requests
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from auth_service import oauth
from auth_service.social_links import upsert_social_user
from auth_service.token_service import build_principal_with_token, set_token_cookie


def _append_params(url: str, **params) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    for key, value in params.items():
        if value is not None:
            query[key] = value
    new_query = urlencode(query)
    return urlunparse(parsed._replace(query=new_query))


def _success_redirect(token: str, redirect_target: str | None) -> HttpResponseRedirect:
    target = redirect_target or settings.OAUTH_REDIRECT_SUCCESS
    target_with_token = _append_params(target, token=token)
    response = HttpResponseRedirect(target_with_token)
    set_token_cookie(response, token)
    return response


def _error_redirect(reason: str) -> HttpResponseRedirect:
    target = _append_params(settings.OAUTH_REDIRECT_ERROR, error=reason)
    return HttpResponseRedirect(target)


class GoogleOAuthStart(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        redirect_target = request.query_params.get("redirect")
        state = oauth.create_state("google", redirect_target)
        redirect_uri = request.build_absolute_uri(reverse("oauth-google-callback"))
        auth_url = oauth.google_authorize_url(redirect_uri, state)
        return HttpResponseRedirect(auth_url)


class GoogleOAuthCallback(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        state = request.query_params.get("state")
        code = request.query_params.get("code")
        if not state or not code:
            return _error_redirect("missing_code")
        try:
            state_data = oauth.consume_state(state)
        except ValueError:
            return _error_redirect("invalid_state")
        redirect_uri = request.build_absolute_uri(reverse("oauth-google-callback"))
        try:
            tokens = oauth.google_tokens(code, redirect_uri)
            identity = oauth.google_identity(tokens["id_token"])
        except (requests.RequestException, KeyError):
            return _error_redirect("google_exchange_error")
        user = upsert_social_user(
            provider=identity["provider"],
            provider_user_id=identity["providerUserId"],
            email=identity.get("email"),
            name=identity.get("name"),
            email_verified=identity.get("email_verified", False),
        )
        token, _ = build_principal_with_token(user)
        return _success_redirect(token, state_data.get("redirect"))


class MicrosoftOAuthStart(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        redirect_target = request.query_params.get("redirect")
        state = oauth.create_state("microsoft", redirect_target)
        redirect_uri = request.build_absolute_uri(reverse("oauth-microsoft-callback"))
        auth_url = oauth.microsoft_authorize_url(redirect_uri, state)
        return HttpResponseRedirect(auth_url)


class MicrosoftOAuthCallback(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        state = request.query_params.get("state")
        code = request.query_params.get("code")
        if not state or not code:
            return _error_redirect("missing_code")
        try:
            state_data = oauth.consume_state(state)
        except ValueError:
            return _error_redirect("invalid_state")
        redirect_uri = request.build_absolute_uri(reverse("oauth-microsoft-callback"))
        try:
            tokens = oauth.microsoft_tokens(code, redirect_uri)
            identity = oauth.microsoft_identity(tokens["id_token"])
        except (requests.RequestException, KeyError):
            return _error_redirect("microsoft_exchange_error")
        user = upsert_social_user(
            provider=identity["provider"],
            provider_user_id=identity["providerUserId"],
            email=identity.get("email"),
            name=identity.get("name"),
            email_verified=identity.get("email_verified", False),
        )
        token, _ = build_principal_with_token(user)
        return _success_redirect(token, state_data.get("redirect"))
