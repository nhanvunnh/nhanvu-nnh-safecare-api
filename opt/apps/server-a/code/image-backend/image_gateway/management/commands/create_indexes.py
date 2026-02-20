from django.core.management.base import BaseCommand

from image_gateway.cleanup_log import COLLECTION
from image_gateway.mongo import get_collection


class Command(BaseCommand):
    help = "Create indexes for image gateway collections"

    def handle(self, *args, **options):
        col = get_collection(COLLECTION)
        col.create_index([("timeCreate", -1)], name="idx_timeCreate_desc")
        col.create_index([("status", 1), ("timeCreate", -1)], name="idx_status_time")
        self.stdout.write(self.style.SUCCESS("Indexes created"))
