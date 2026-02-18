from __future__ import annotations

from typing import Iterable, Optional

from auth_service import utils
from auth_service.constants import LEVEL_CUSTOMER, STATUS_ACTIVE
from auth_service.models import User, UserGroup
from auth_service.passwords import hash_password


def find_user_by_identifier(identifier: str) -> Optional[User]:
    normalized_email = utils.normalize_email(identifier)
    if normalized_email:
        user = User.objects(email=normalized_email).first()
        if user:
            return user
    normalized_phone = utils.normalize_phone(identifier)
    if normalized_phone:
        return User.objects(phone=normalized_phone).first()
    return None


def get_user_by_id(user_id: str) -> Optional[User]:
    return User.objects(id=user_id).first()


def create_user(
    *,
    email: str | None,
    phone: str | None,
    full_name: str,
    password: str,
    level: str = LEVEL_CUSTOMER,
    status: str = STATUS_ACTIVE,
    groups: Iterable[str] | None = None,
    extra_perms: Iterable[str] | None = None,
    verified_email: bool = False,
    verified_phone: bool = False,
) -> User:
    email = utils.normalize_email(email)
    phone = utils.normalize_phone(phone)
    ensure_unique_contact(email=email, phone=phone, exclude_id=None)
    user = User(
        email=email,
        phone=phone,
        fullName=full_name,
        passwordHash=hash_password(password),
        level=level,
        status=status,
        groups=list(groups or []),
        extraPerms=list(extra_perms or []),
        verifiedEmail=verified_email,
        verifiedPhone=verified_phone,
    )
    user.save()
    return user


def ensure_unique_contact(*, email: str | None, phone: str | None, exclude_id: str | None = None) -> None:
    normalized_email = utils.normalize_email(email)
    if normalized_email:
        query = User.objects(email=normalized_email)
        if exclude_id:
            query = query.filter(id__ne=exclude_id)
        if query.first():
            raise ValueError("Email already in use")
    normalized_phone = utils.normalize_phone(phone)
    if normalized_phone:
        query = User.objects(phone=normalized_phone)
        if exclude_id:
            query = query.filter(id__ne=exclude_id)
        if query.first():
            raise ValueError("Phone already in use")


def set_password(user: User, password: str) -> None:
    user.passwordHash = hash_password(password)
    user.save()


def update_user(user: User, **fields) -> User:
    for key, value in fields.items():
        if value is None:
            continue
        setattr(user, key, value)
    user.save()
    return user


def ensure_groups_exist(groups: Iterable[str]) -> None:
    missing = []
    for code in groups:
        if not UserGroup.objects(code=code).first():
            missing.append(code)
    if missing:
        raise ValueError(f"Groups not found: {', '.join(missing)}")


def record_login(user: User) -> None:
    user.lastLoginAt = utils.utcnow()
    user.save()
