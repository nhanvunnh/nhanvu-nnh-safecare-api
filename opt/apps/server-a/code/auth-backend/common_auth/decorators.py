from __future__ import annotations

from functools import wraps
from typing import Callable, Iterable

from common_auth import errors


def _get_principal(request):
    principal = getattr(request, "principal", None)
    if principal is None:
        raise errors.MissingTokenError()
    return principal


def require_auth(view_func: Callable):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        _get_principal(request)
        return view_func(request, *args, **kwargs)

    return wrapper


def require_levels(levels: Iterable[str]):
    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            principal = _get_principal(request)
            if principal.level not in levels:
                raise errors.AuthError("insufficient_level", "Forbidden")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_perm(perm: str):
    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            principal = _get_principal(request)
            if perm not in principal.perms:
                raise errors.AuthError("missing_permission", "Forbidden")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
