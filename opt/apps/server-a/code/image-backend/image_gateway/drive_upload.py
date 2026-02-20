import json
import os
import uuid

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials


def _get_session(sa_file):
    scopes = ["https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(sa_file, scopes=scopes)
    return AuthorizedSession(creds)


def _guess_mime(filename, default="application/octet-stream"):
    ext = os.path.splitext(str(filename or ""))[1].lower()
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    return default


def upload_bytes_to_drive(content, filename, folder_id, sa_file, mime_type=None):
    if not (content and filename and folder_id and sa_file and os.path.isfile(sa_file)):
        return None
    mime_type = mime_type or _guess_mime(filename)
    boundary = "-------" + uuid.uuid4().hex
    metadata = {"name": filename, "parents": [folder_id]}
    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        + json.dumps(metadata)
        + "\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")

    headers = {"Content-Type": f"multipart/related; boundary={boundary}"}
    session = _get_session(sa_file)
    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name"
    resp = session.post(url, data=body, headers=headers, timeout=30)
    if resp.status_code in [200, 201]:
        return resp.json()
    return None


def delete_drive_file_by_name(filename, folder_id, sa_file):
    if not (filename and folder_id and sa_file and os.path.isfile(sa_file)):
        return False
    session = _get_session(sa_file)
    q = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
    list_url = "https://www.googleapis.com/drive/v3/files"
    list_resp = session.get(list_url, params={"q": q, "fields": "files(id)"}, timeout=15)
    if list_resp.status_code != 200:
        return False
    files = list_resp.json().get("files", [])
    ok = True
    for f in files:
        file_id = f.get("id")
        if not file_id:
            continue
        del_url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        del_resp = session.delete(del_url, timeout=15)
        if del_resp.status_code not in [200, 204]:
            ok = False
    return ok
