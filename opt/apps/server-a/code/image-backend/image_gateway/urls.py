from django.urls import re_path

from .health import HealthView
from .views import (
    DriveDeleteView,
    DriveUploadView,
    GnhImageView,
    GoodImageView,
    S3DeleteView,
    S3UploadView,
)

urlpatterns = [
    re_path(r"^health/?$", HealthView.as_view(), name="health"),
    re_path(r"^get_image/?$", GnhImageView.as_view(), name="get-image"),
    re_path(r"^good_image/?$", GoodImageView.as_view(), name="good-image"),
    re_path(r"^drive/upload/?$", DriveUploadView.as_view(), name="drive-upload"),
    re_path(r"^drive/delete/?$", DriveDeleteView.as_view(), name="drive-delete"),
    re_path(r"^s3/upload/?$", S3UploadView.as_view(), name="s3-upload"),
    re_path(r"^s3/delete/?$", S3DeleteView.as_view(), name="s3-delete"),
]
