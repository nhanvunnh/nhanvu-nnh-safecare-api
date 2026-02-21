from django.conf import settings
from django.urls import include, path

from sheet_sync_gateway.health import HealthView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
]

prefix = settings.BASE_PATH.lstrip("/")
if prefix:
    urlpatterns.append(path(f"{prefix}/health", HealthView.as_view(), name="prefixed-health"))
    urlpatterns.append(path(f"{prefix}/", include("sheet_sync_gateway.urls")))
else:
    urlpatterns.append(path("", include("sheet_sync_gateway.urls")))
