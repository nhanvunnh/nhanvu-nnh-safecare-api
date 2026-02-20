import os
from io import BytesIO

from PIL import Image
from django.conf import settings

from .cache_cleanup import maybe_cleanup_cache_async
from .drive_image import load_drive_image
from .s3_store import get_s3_object


def _ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def _image_mime_by_ext(ext):
    if ext == ".png":
        return "image/png"
    return "image/jpeg"


def _detect_ext(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".jpg", ".jpeg", ".png"]:
        return ext
    return ".jpg"


def _resize_image(content, width, ext):
    img = Image.open(BytesIO(content))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    if w <= width:
        return content
    new_h = int(h * (width / float(w)))
    img = img.resize((width, new_h), Image.LANCZOS)
    out = BytesIO()
    if ext == ".png":
        img.save(out, format="PNG", optimize=True)
    else:
        img.save(out, format="JPEG", quality=85, optimize=True)
    return out.getvalue()


def fetch_cached_image(
    file_path,
    *,
    source="drive",
    folder_id=None,
    cache_dir=None,
    width=None,
    cache_max_bytes=0,
    cache_max_days=0,
    aws_bucket=None,
):
    if not file_path:
        return None, None

    if source == "drive":
        if not (folder_id and cache_dir):
            return None, None
        _ensure_dir(cache_dir)
        maybe_cleanup_cache_async(cache_dir, cache_max_bytes, cache_max_days)
        return load_drive_image(file_path, folder_id, settings.GOOGLE_SERVICE_ACCOUNT_FILE, cache_dir, width=width)

    if source == "local":
        rel_path = file_path.lstrip("/\\")
        abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        if not os.path.isfile(abs_path):
            return None, None
        with open(abs_path, "rb") as f:
            content = f.read()
        ext = _detect_ext(abs_path)
        if width:
            content = _resize_image(content, width, ext)
        return content, _image_mime_by_ext(ext)

    if source == "s3":
        if not (cache_dir and aws_bucket):
            return None, None
        if not file_path.startswith(aws_bucket):
            return None, None

        _ensure_dir(cache_dir)
        maybe_cleanup_cache_async(cache_dir, cache_max_bytes, cache_max_days)

        key = file_path.replace(aws_bucket, "").lstrip("/")
        ext = _detect_ext(key)
        base_name = os.path.splitext(key)[0]
        cache_name = f"{base_name}.w{width}{ext}" if width else f"{base_name}{ext}"
        cache_path = os.path.join(cache_dir, cache_name)
        _ensure_dir(os.path.dirname(cache_path))

        if os.path.isfile(cache_path):
            with open(cache_path, "rb") as f:
                return f.read(), _image_mime_by_ext(ext)

        try:
            obj = get_s3_object(key)
            if obj is None:
                return None, None
            content = obj["Body"].read()
            mime = obj.get("ContentType") or _image_mime_by_ext(ext)
        except Exception:
            return None, None

        if width:
            content = _resize_image(content, width, ext)

        try:
            with open(cache_path, "wb") as f:
                f.write(content)
        except Exception:
            pass

        return content, mime

    return None, None
