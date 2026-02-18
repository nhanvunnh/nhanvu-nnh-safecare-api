from __future__ import annotations

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from auth_service.constants import LEVEL_ORDER, LEVEL_ROOT


class PrincipalRequired(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request, "principal", None))


def ensure_level(principal, min_level: str) -> None:
    if principal.level == LEVEL_ROOT:
        return
    if LEVEL_ORDER.get(principal.level, -1) < LEVEL_ORDER.get(min_level, -1):
        raise PermissionDenied("Insufficient level")


def ensure_perm(principal, perm: str) -> None:
    if principal.level == LEVEL_ROOT:
        return
    if perm not in principal.perms and "*" not in principal.perms:
        raise PermissionDenied("Missing permission")
