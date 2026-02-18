from django.core.management.base import BaseCommand

from auth_service.models import GroupPermission, PasswordResetToken, User, UserGroup, UserSocialLink


class Command(BaseCommand):
    help = "Create MongoDB indexes for auth service collections"

    def handle(self, *args, **options):
        for document in [User, UserGroup, GroupPermission, UserSocialLink, PasswordResetToken]:
            self.stdout.write(f"Ensuring indexes for {document.__name__}...")
            document.ensure_indexes()
        self.stdout.write(self.style.SUCCESS("Indexes ensured."))
