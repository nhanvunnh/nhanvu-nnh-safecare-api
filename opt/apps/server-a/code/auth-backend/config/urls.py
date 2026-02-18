from django.conf import settings
from django.urls import include, path

from auth_service.views.health import health_view

urlpatterns = [
    path("health", health_view, name="health"),
]

prefix = settings.BASE_PATH.lstrip("/")
if prefix:
    urlpatterns.append(path(f"{prefix}/", include("auth_service.urls")))
else:
    urlpatterns.append(path("", include("auth_service.urls")))
