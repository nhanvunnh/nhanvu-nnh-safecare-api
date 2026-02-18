from __future__ import annotations

from typing import Iterable, Set

from auth_service.constants import LEVEL_ORDER, LEVEL_ROOT
from auth_service.models import GroupPermission, User, UserGroup


def _group_permissions(group_code: str) -> Set[str]:
    return {perm.perm for perm in GroupPermission.objects(groupCode=group_code)}


def get_user_permissions(user: User) -> Set[str]:
    if user.level == LEVEL_ROOT:
        return {"*"}
    permissions: Set[str] = set(user.extraPerms or [])
    for code in user.groups or []:
        permissions.update(_group_permissions(code))
    return permissions


def has_perm(user: User, perm: str) -> bool:
    if user.level == LEVEL_ROOT:
        return True
    perms = get_user_permissions(user)
    return "*" in perms or perm in perms


def has_level_at_least(level: str, required_level: str) -> bool:
    return LEVEL_ORDER.get(level, -1) >= LEVEL_ORDER.get(required_level, -1)


def _level_value(level_or_obj) -> str:
    if hasattr(level_or_obj, "level"):
        return getattr(level_or_obj, "level")
    return str(level_or_obj)


def ensure_level_hierarchy(actor_level, target_level: str) -> None:
    actor_current = _level_value(actor_level)
    if actor_current == LEVEL_ROOT:
        return
    if not has_level_at_least(actor_current, target_level):
        raise PermissionError("Cannot assign higher level than caller")


def ensure_groups_exist(groups: Iterable[str]) -> None:
    missing = []
    for code in groups:
        if not UserGroup.objects(code=code).first():
            missing.append(code)
    if missing:
        raise ValueError(f"Missing group permissions for: {', '.join(missing)}")
