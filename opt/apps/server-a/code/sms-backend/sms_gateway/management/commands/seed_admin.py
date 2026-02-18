from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed Django admin user if SEED_ADMIN=1"

    def handle(self, *args, **options):
        if not settings.SEED_ADMIN:
            self.stdout.write("SEED_ADMIN disabled; skipping admin creation.")
            return

        User = get_user_model()
        username = settings.SEED_ADMIN_USERNAME
        password = settings.SEED_ADMIN_PASSWORD

        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Admin user '{username}' already exists.")
            return

        User.objects.create_superuser(username=username, email=f"{username}@example.com", password=password)
        self.stdout.write(self.style.SUCCESS(f"Admin user '{username}' created."))
