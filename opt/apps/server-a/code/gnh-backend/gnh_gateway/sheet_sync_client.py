import requests
from django.conf import settings


class SheetSyncError(Exception):
    pass


def _base_url():
    return settings.SHEET_SYNC_BASE_URL.rstrip("/")


def _payload_base():
    payload = {}
    token = settings.SHEET_SYNC_SERVICE_TOKEN
    if token:
        payload["service_token"] = token
    return payload


def run_sheet_sync(app_code="gnh", direction="manual", delete_key=""):
    if not settings.SHEET_SYNC_ENABLED:
        raise SheetSyncError("Sheet sync service disabled")

    payload = _payload_base()
    payload.update({"app_code": app_code, "direction": direction})
    if delete_key:
        payload["delete_key"] = delete_key

    url = f"{_base_url()}/jobs/run"
    try:
        resp = requests.post(url, json=payload, timeout=30)
    except Exception as exc:
        raise SheetSyncError(str(exc))

    try:
        body = resp.json()
    except Exception:
        body = {"Error": resp.text}

    if resp.status_code >= 400:
        raise SheetSyncError(body.get("Error") or f"HTTP {resp.status_code}")
    return body


def fetch_sheet_logs(app_code="gnh", page=1, page_size=50, status_filter=""):
    if not settings.SHEET_SYNC_ENABLED:
        raise SheetSyncError("Sheet sync service disabled")

    payload = _payload_base()
    payload.update({"app_code": app_code, "page": page, "page_size": page_size})
    if status_filter:
        payload["status"] = status_filter

    url = f"{_base_url()}/logs/list"
    try:
        resp = requests.post(url, json=payload, timeout=30)
    except Exception as exc:
        raise SheetSyncError(str(exc))

    try:
        body = resp.json()
    except Exception:
        body = {"Error": resp.text}

    if resp.status_code >= 400:
        raise SheetSyncError(body.get("Error") or f"HTTP {resp.status_code}")
    return body
