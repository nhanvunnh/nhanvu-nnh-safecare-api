from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("image_gateway.urls")),
    path("admin/", admin.site.urls),
]
