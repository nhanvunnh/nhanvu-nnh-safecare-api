import datetime

from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def utcnow():
    return datetime.datetime.utcnow()


def scope_rank(scope):
    order = {"read": 1, "write": 2, "admin": 3}
    return order.get((scope or "").lower(), 0)


def has_scope(scope, required_scope):
    return scope_rank(scope) >= scope_rank(required_scope)


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
    return dt_value.astimezone(VN_TZ).strftime("%d/%m/%Y %H:%M:%S")
