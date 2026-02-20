import os

from django.conf import settings
import boto3


def _build_s3_client():
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        return None
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


s3 = _build_s3_client()


def normalize_s3_key(folder, filename):
    folder = str(folder or "").replace("\\", "/").strip("/")
    filename = str(filename or "").replace("\\", "/").lstrip("/")
    if folder:
        return f"{folder}/{filename}"
    return filename


def upload_bytes_to_s3(content, target_folder, target_filename, mime_type="application/octet-stream"):
    if not content or not settings.ENABLE_S3 or not s3:
        return ""
    key = normalize_s3_key(target_folder, target_filename)
    s3.put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key,
        Body=content,
        ACL="public-read",
        ContentType=mime_type,
    )
    if not settings.AWS_BUCKET:
        return key
    return settings.AWS_BUCKET + key


def delete_s3_by_url(url):
    if not url or not settings.AWS_BUCKET or not s3:
        return False
    if not str(url).startswith(settings.AWS_BUCKET):
        return False
    key = str(url).replace(settings.AWS_BUCKET, "")
    s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
    return True


def get_s3_object(key):
    if not s3:
        return None
    return s3.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
