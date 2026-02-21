from django.core.management.base import BaseCommand

from sheet_sync_gateway.indexes import create_indexes


class Command(BaseCommand):
    help = "Create indexes for sheet-sync collections"

    def handle(self, *args, **options):
        create_indexes()
        self.stdout.write(self.style.SUCCESS("Indexes created"))
