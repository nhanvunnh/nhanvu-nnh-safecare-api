from django.core.management.base import BaseCommand

from gnh_gateway.indexes import create_indexes


class Command(BaseCommand):
    help = "Create indexes for GNH collections"

    def handle(self, *args, **options):
        create_indexes()
        self.stdout.write(self.style.SUCCESS("Indexes created"))
