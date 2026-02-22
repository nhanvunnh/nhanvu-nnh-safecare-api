from __future__ import annotations

import os
from typing import Iterable

from django.core.management.base import BaseCommand, CommandError

from auth_service import services, utils
from auth_service.constants import LEVEL_ADMIN, LEVELS, STATUS_ACTIVE
from auth_service.models import User
from auth_service.passwords import hash_password


def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str | None, *, upper: bool = False) -> list[str]:
    parts = [item.strip() for item in (value or "").split(",")]
    items = [item for item in parts if item]
    if upper:
        items = [item.upper() for item in items]
    return items


def _ensure_groups(groups: Iterable[str]) -> None:
    if groups:
        services.ensure_groups_exist(groups)


class Command(BaseCommand):
    help = "Create or update a default admin user from environment variables"

    def handle(self, *args, **options):
        if not _is_truthy(os.environ.get("DEFAULT_ADMIN_ENABLED", "0")):
            self.stdout.write("DEFAULT_ADMIN_ENABLED is false. Skip default admin creation.")
            return

        email = utils.normalize_email(os.environ.get("DEFAULT_ADMIN_EMAIL"))
        phone = utils.normalize_phone(os.environ.get("DEFAULT_ADMIN_PHONE"))
        if not email and not phone:
            raise CommandError("Provide DEFAULT_ADMIN_EMAIL or DEFAULT_ADMIN_PHONE when DEFAULT_ADMIN_ENABLED=1")

        password = (os.environ.get("DEFAULT_ADMIN_PASSWORD") or "").strip()
        if not password:
            raise CommandError("DEFAULT_ADMIN_PASSWORD is required when DEFAULT_ADMIN_ENABLED=1")

        full_name = (os.environ.get("DEFAULT_ADMIN_FULL_NAME") or "Default Admin").strip() or "Default Admin"
        level = (os.environ.get("DEFAULT_ADMIN_LEVEL") or LEVEL_ADMIN).strip() or LEVEL_ADMIN
        if level not in LEVELS:
            raise CommandError(f"DEFAULT_ADMIN_LEVEL must be one of: {', '.join(LEVELS)}")

        groups = _parse_csv(os.environ.get("DEFAULT_ADMIN_GROUPS", "ADMIN"), upper=True)
        extra_perms = _parse_csv(os.environ.get("DEFAULT_ADMIN_EXTRA_PERMS"))
        reset_password = _is_truthy(os.environ.get("DEFAULT_ADMIN_RESET_PASSWORD", "0"))

        _ensure_groups(groups)

        user_by_email = User.objects(email=email).first() if email else None
        user_by_phone = User.objects(phone=phone).first() if phone else None
        if user_by_email and user_by_phone and str(user_by_email.id) != str(user_by_phone.id):
            raise CommandError("DEFAULT_ADMIN_EMAIL and DEFAULT_ADMIN_PHONE point to different users")

        user = user_by_email or user_by_phone
        if not user:
            created = services.create_user(
                email=email,
                phone=phone,
                full_name=full_name,
                password=password,
                level=level,
                status=STATUS_ACTIVE,
                groups=groups,
                extra_perms=extra_perms,
                verified_email=bool(email),
                verified_phone=bool(phone),
            )
            self.stdout.write(self.style.SUCCESS(f"Created default admin user: {created.email or created.phone}"))
            return

        changed = False
        services.ensure_unique_contact(email=email, phone=phone, exclude_id=str(user.id))
        if email and user.email != email:
            user.email = email
            changed = True
        if phone and user.phone != phone:
            user.phone = phone
            changed = True
        if user.fullName != full_name:
            user.fullName = full_name
            changed = True
        if user.level != level:
            user.level = level
            changed = True
        if user.status != STATUS_ACTIVE:
            user.status = STATUS_ACTIVE
            changed = True
        if groups and list(user.groups or []) != groups:
            user.groups = groups
            changed = True
        if list(user.extraPerms or []) != extra_perms:
            user.extraPerms = extra_perms
            changed = True
        if email and not user.verifiedEmail:
            user.verifiedEmail = True
            changed = True
        if phone and not user.verifiedPhone:
            user.verifiedPhone = True
            changed = True
        if reset_password:
            user.passwordHash = hash_password(password)
            changed = True

        if changed:
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Updated default admin user: {user.email or user.phone}"))
        else:
            self.stdout.write(f"Default admin user already up to date: {user.email or user.phone}")
