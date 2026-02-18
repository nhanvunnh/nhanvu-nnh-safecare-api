from django.core.management.base import BaseCommand

from sms_gateway.indexes import create_indexes


class Command(BaseCommand):
    help = "Create MongoDB indexes for SMS gateway collections"

    def handle(self, *args, **options):
        create_indexes()
        self.stdout.write(self.style.SUCCESS("MongoDB indexes created."))
