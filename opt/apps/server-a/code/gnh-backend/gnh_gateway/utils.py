import datetime
from urllib.parse import quote

from zoneinfo import ZoneInfo

from django.conf import settings

from gnh_gateway.models import GNH_DATE_FORMAT, GNH_FIELDS

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def get_param(request, key, default=None):
    for source_name in ("data", "POST", "GET"):
        source = getattr(request, source_name, None)
        if source is None:
            continue
        try:
            value = source.get(key, default)
        except Exception:
            continue
        if value is None:
            return default
        return value
    return default


def has_param(request, key):
    value = get_param(request, key, None)
    return value is not None and value != ""


def parse_int(value, fallback):
    try:
        return int(value)
    except Exception:
        return fallback


def fmt_dt(dt_value):
    if not dt_value:
        return ""
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=datetime.timezone.utc)
    return dt_value.astimezone(VN_TZ).strftime(GNH_DATE_FORMAT)


def parse_sheet_dt(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        local_dt = datetime.datetime.strptime(text, GNH_DATE_FORMAT).replace(tzinfo=VN_TZ)
        return local_dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def parse_row_sort_dt(row):
    date_str = str(row.get("NGAY_NHAN") or "").strip()
    time_str = str(row.get("GIO_NHAN") or "").strip()
    if not date_str:
        return datetime.datetime.min
    candidate = f"{date_str} {time_str}".strip()
    patterns = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for pattern in patterns:
        try:
            return datetime.datetime.strptime(candidate, pattern)
        except Exception:
            continue
    return datetime.datetime.min


def normalize_doc(doc):
    item = {}
    for field in GNH_FIELDS:
        value = doc.get(field, "")
        if field == "UPDATED_AT":
            item[field] = fmt_dt(value)
        else:
            item[field] = value if value is not None else ""
    return item


def to_image_url(raw_value):
    val = str(raw_value or "").strip()
    if not val:
        return ""
    if val.startswith("http://") or val.startswith("https://"):
        return val
    return f"{settings.IMAGE_SERVICE_BASE_URL}/get_image?file={quote(val)}"
