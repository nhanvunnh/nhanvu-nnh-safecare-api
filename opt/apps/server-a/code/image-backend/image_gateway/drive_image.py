import os
import time

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials
from PIL import Image
from io import BytesIO


_CACHE = {}
_CACHE_TTL = 600


def _get_session(sa_file):
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_file(sa_file, scopes=scopes)
    return AuthorizedSession(creds)


def _ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def _detect_ext(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".jpg", ".jpeg", ".png"]:
        return ext
    return ".jpg"


def _image_mime_by_ext(ext):
    if ext == ".png":
        return "image/png"
    return "image/jpeg"


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


def load_drive_image(file_path, folder_id, sa_file, cache_dir, width=None):
    if not file_path or not folder_id or not sa_file or not os.path.isfile(sa_file):
        return None, None

    filename = os.path.basename(file_path)
    ext = _detect_ext(filename)
    _ensure_dir(cache_dir)

    base_name = os.path.splitext(filename)[0]
    cache_name = f"{base_name}.w{width}{ext}" if width else f"{base_name}{ext}"
    cache_path = os.path.join(cache_dir, cache_name)
    if os.path.isfile(cache_path):
        with open(cache_path, "rb") as f:
            return f.read(), _image_mime_by_ext(ext)

    cache_key = f"drv:{folder_id}:{filename}"
    now_ts = time.time()
    cache_entry = _CACHE.get(cache_key)

    file_id = None
    if cache_entry and (now_ts - cache_entry["ts"] < _CACHE_TTL):
        file_id = cache_entry.get("id")
    else:
        authed = _get_session(sa_file)
        q = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
        list_url = "https://www.googleapis.com/drive/v3/files"
        list_resp = authed.get(list_url, params={"q": q, "fields": "files(id,mimeType)"}, timeout=15)
        if list_resp.status_code == 200:
            files = list_resp.json().get("files", [])
            if files:
                file_id = files[0]["id"]
                _CACHE[cache_key] = {"id": file_id, "ts": now_ts}
            else:
                _CACHE[cache_key] = {"id": None, "ts": now_ts}

    if not file_id:
        return None, None

    authed = _get_session(sa_file)
    dl_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    dl_resp = authed.get(dl_url, timeout=30)
    if dl_resp.status_code != 200:
        return None, None

    content = dl_resp.content
    if width:
        content = _resize_image(content, width, ext)

    with open(cache_path, "wb") as f:
        f.write(content)

    return content, _image_mime_by_ext(ext)
