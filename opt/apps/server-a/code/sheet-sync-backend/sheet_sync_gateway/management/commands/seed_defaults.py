from django.conf import settings
from django.core.management.base import BaseCommand

from sheet_sync_gateway.models import COL_APP_CONFIGS
from sheet_sync_gateway.mongo import get_collection


class Command(BaseCommand):
    help = "Seed default app config(s) for sheet sync"

    def handle(self, *args, **options):
        if not settings.DEFAULT_GNH_ENABLED:
            self.stdout.write(self.style.WARNING("DEFAULT_GNH_ENABLED is false, skip seed"))
            return

        payload = {
            "app_code": "gnh",
            "name": "Giao Nhan Hang",
            "sheet_name": settings.DEFAULT_GNH_SHEET_NAME,
            "worksheet_name": settings.DEFAULT_GNH_WORKSHEET_NAME,
            "target_db": settings.DEFAULT_GNH_TARGET_DB,
            "target_collection": settings.DEFAULT_GNH_TARGET_COLLECTION,
            "key_field": settings.DEFAULT_GNH_KEY_FIELD,
            "updated_at_field": settings.DEFAULT_GNH_UPDATED_AT_FIELD,
            "date_format": settings.DEFAULT_GNH_DATE_FORMAT,
            "fields": settings.DEFAULT_GNH_FIELDS,
            "is_active": True,
        }

        get_collection(COL_APP_CONFIGS).update_one(
            {"app_code": payload["app_code"]},
            {"$set": payload},
            upsert=True,
        )
        self.stdout.write(self.style.SUCCESS("Seeded default app config: gnh"))
