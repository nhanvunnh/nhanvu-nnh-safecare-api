from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("", include("sms_gateway.urls")),
    path("admin/", admin.site.urls),
]
