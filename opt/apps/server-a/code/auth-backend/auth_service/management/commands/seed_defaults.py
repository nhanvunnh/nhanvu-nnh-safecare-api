from __future__ import annotations

from django.core.management.base import BaseCommand

from auth_service.constants import DEFAULT_GROUPS, LEVEL_ADMIN, LEVEL_ROOT
from auth_service.models import GroupPermission, User, UserGroup


class Command(BaseCommand):
    help = "Seed default RBAC groups and permissions"

    def handle(self, *args, **options):
        for code, meta in DEFAULT_GROUPS.items():
            group = UserGroup.objects(code=code).first()
            created = False
            if not group:
                group = UserGroup(
                    code=code,
                    name=meta.get("name", code.title()),
                    description=meta.get("description", ""),
                )
                group.save()
                created = True
            if created:
                self.stdout.write(f"Created group {code}")
            for perm in meta.get("perms", []):
                if not GroupPermission.objects(groupCode=code, perm=perm).first():
                    GroupPermission(groupCode=code, perm=perm).save()
        for user in User.objects:
            if user.level == LEVEL_ROOT and not user.groups:
                user.groups = ["ROOT"]
                user.save()
                self.stdout.write(f"Assigned ROOT group to {user.fullName}")
            elif user.level == LEVEL_ADMIN and not user.groups:
                user.groups = ["ADMIN"]
                user.save()
                self.stdout.write(f"Assigned ADMIN group to {user.fullName}")
        self.stdout.write(self.style.SUCCESS("Default groups and permissions seeded."))
