import base64
import os

from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .drive_upload import delete_drive_file_by_name, upload_bytes_to_drive
from .health import HealthView
from .image_store import fetch_cached_image
from .s3_store import delete_s3_by_url, upload_bytes_to_s3


def _read_upload_content(request):
    upload = request.FILES.get("file")
    if upload is not None:
        return upload.read(), upload.name, upload.content_type or "application/octet-stream"

    payload = request.data or {}
    content_b64 = payload.get("content_base64")
    filename = str(payload.get("filename") or "")
    mime_type = str(payload.get("mime_type") or "application/octet-stream")
    if not content_b64:
        return None, filename, mime_type
    try:
        return base64.b64decode(content_b64), filename, mime_type
    except Exception:
        return None, filename, mime_type


class GnhImageView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        file_path = str(request.GET.get("file", "")).strip()
        if not file_path:
            return HttpResponse(status=400)
        try:
            width = request.GET.get("w")
            width = int(width) if width and str(width).isdigit() else None
            content, mime = fetch_cached_image(
                file_path,
                source="drive",
                folder_id=getattr(settings, "GNH_IMAGES_DRIVE_FOLDER_ID", ""),
                cache_dir=getattr(settings, "GNH_IMAGE_CACHE_DIR", ""),
                width=width,
                cache_max_bytes=getattr(settings, "GNH_IMAGE_CACHE_MAX_BYTES", 0),
                cache_max_days=getattr(settings, "GNH_IMAGE_CACHE_MAX_DAYS", 0),
            )
            if content:
                return HttpResponse(content, content_type=mime or "application/octet-stream")
            if getattr(settings, "DEBUG", False):
                return HttpResponse("Drive file not found", status=404)
            return HttpResponse(status=404)
        except Exception:
            return HttpResponse(status=502)


class GoodImageView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        file_path = str(request.GET.get("file", "")).strip()
        if not file_path:
            return HttpResponse(status=400)
        try:
            width = request.GET.get("w")
            width = int(width) if width and str(width).isdigit() else None
            drive_prefix = "drive:"
            if file_path.startswith(drive_prefix):
                content, mime = fetch_cached_image(
                    file_path[len(drive_prefix) :],
                    source="drive",
                    folder_id=getattr(settings, "GOOD_IMAGES_DRIVE_FOLDER_ID", ""),
                    cache_dir=getattr(settings, "GOOD_IMAGE_CACHE_DIR", ""),
                    width=width,
                    cache_max_bytes=getattr(settings, "GOOD_IMAGE_CACHE_MAX_BYTES", 0),
                    cache_max_days=getattr(settings, "GOOD_IMAGE_CACHE_MAX_DAYS", 0),
                )
            elif file_path.startswith("http://") or file_path.startswith("https://"):
                content, mime = fetch_cached_image(
                    file_path,
                    source="s3",
                    cache_dir=getattr(settings, "GOOD_IMAGE_CACHE_DIR", ""),
                    width=width,
                    cache_max_bytes=getattr(settings, "GOOD_IMAGE_CACHE_MAX_BYTES", 0),
                    cache_max_days=getattr(settings, "GOOD_IMAGE_CACHE_MAX_DAYS", 0),
                    aws_bucket=getattr(settings, "AWS_BUCKET", ""),
                )
            else:
                content, mime = fetch_cached_image(file_path, source="local", width=width)

            if content:
                return HttpResponse(content, content_type=mime or "application/octet-stream")
            if getattr(settings, "DEBUG", False):
                return HttpResponse("Image not found", status=404)
            return HttpResponse(status=404)
        except Exception:
            return HttpResponse(status=502)


class DriveUploadView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.data or {}
        folder_id = str(payload.get("folder_id") or settings.GOOD_IMAGES_DRIVE_FOLDER_ID)
        content, filename, mime_type = _read_upload_content(request)
        filename = str(filename or payload.get("filename") or "").strip()
        if not folder_id or not filename or not content:
            return Response({"detail": "folder_id, filename, content required"}, status=status.HTTP_400_BAD_REQUEST)

        drive_name = str(payload.get("drive_name") or filename).strip()
        res = upload_bytes_to_drive(content, drive_name, folder_id, settings.GOOGLE_SERVICE_ACCOUNT_FILE, mime_type=mime_type)
        if not res:
            return Response({"detail": "Drive upload failed"}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "status": "ok",
                "drive": res,
                "path": f"drive:{drive_name}",
            }
        )


class DriveDeleteView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.data or {}
        folder_id = str(payload.get("folder_id") or settings.GOOD_IMAGES_DRIVE_FOLDER_ID)
        name = str(payload.get("filename") or payload.get("path") or "").strip()
        if name.startswith("drive:"):
            name = name.replace("drive:", "", 1)
        if not folder_id or not name:
            return Response({"detail": "folder_id and filename/path required"}, status=status.HTTP_400_BAD_REQUEST)

        ok = delete_drive_file_by_name(name, folder_id, settings.GOOGLE_SERVICE_ACCOUNT_FILE)
        if not ok:
            return Response({"detail": "Drive delete failed"}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"status": "ok"})


class S3UploadView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.data or {}
        target_folder = str(payload.get("target_folder") or "good/misc").strip("/\\")
        content, filename, mime_type = _read_upload_content(request)
        filename = str(filename or payload.get("filename") or "").strip()
        if not filename or not content:
            return Response({"detail": "filename and content required"}, status=status.HTTP_400_BAD_REQUEST)

        url = upload_bytes_to_s3(content, target_folder, filename, mime_type=mime_type)
        if not url:
            return Response({"detail": "S3 upload failed"}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "status": "ok",
                "url": url,
                "key": f"{target_folder}/{filename}" if target_folder else filename,
            }
        )


class S3DeleteView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.data or {}
        url = str(payload.get("url") or "").strip()
        if not url:
            return Response({"detail": "url required"}, status=status.HTTP_400_BAD_REQUEST)
        ok = delete_s3_by_url(url)
        if not ok:
            return Response({"detail": "S3 delete failed"}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"status": "ok"})
