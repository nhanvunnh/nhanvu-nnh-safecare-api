from django.conf import settings
from django.core.management.base import BaseCommand

from gnh_gateway.gsheet_sync import run_loop_forever, service_account_exists


class Command(BaseCommand):
    help = "Run GNH Google Sheet sync loop"

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=settings.GNH_SYNC_INTERVAL)

    def handle(self, *args, **options):
        if not service_account_exists():
            raise Exception(f"Service account file not found: {settings.GOOGLE_SERVICE_ACCOUNT_FILE}")
        interval = max(5, int(options["interval"]))
        self.stdout.write(self.style.SUCCESS(f"Start GNH sync loop interval={interval}s"))
        run_loop_forever(interval_seconds=interval)
