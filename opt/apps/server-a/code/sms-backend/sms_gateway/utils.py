import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from bson import ObjectId
from django.conf import settings

from .mongo import get_collection

PLACEHOLDER_PATTERN = re.compile(r"\{([A-Z0-9_]+)\}")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def start_of_day(date: datetime) -> datetime:
    return datetime(date.year, date.month, date.day, tzinfo=timezone.utc)


def end_of_day(date: datetime) -> datetime:
    return start_of_day(date) + timedelta(days=1)


def isoformat(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def generate_token(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_phone(number: str) -> str:
    digits = re.sub(r"[^0-9+]", "", number)
    if not digits:
        raise ValueError("Phone number required")
    if digits.startswith("+"):
        normalized = digits
    elif digits.startswith("00"):
        normalized = "+" + digits[2:]
    elif digits.startswith("0"):
        normalized = settings.DEFAULT_COUNTRY_PREFIX + digits[1:]
    elif digits.startswith(settings.DEFAULT_COUNTRY_PREFIX):
        normalized = digits
    else:
        normalized = settings.DEFAULT_COUNTRY_PREFIX + digits

    if settings.BLOCK_INTERNATIONAL and not normalized.startswith(settings.DEFAULT_COUNTRY_PREFIX):
        raise ValueError("International numbers are blocked")
    return normalized


def extract_template_variables(content: str) -> List[str]:
    return sorted(set(match.group(1) for match in PLACEHOLDER_PATTERN.finditer(content)))


def render_template(content: str, variables: Dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = variables.get(key)
        if value is None:
            raise ValueError(f"Missing variable {key}")
        return str(value)

    return PLACEHOLDER_PATTERN.sub(replace, content)


def vars_hash(variables: Dict[str, Any]) -> str:
    payload = json.dumps(variables, sort_keys=True, separators=(",", ":"))
    return sha256_hex(payload)


def ensure_object_id(value: str) -> ObjectId:
    return ObjectId(value)


def ensure_uuid() -> str:
    return str(uuid.uuid4())


def write_audit_log(actor_type: str, actor_id: str, action: str, data: Dict[str, Any]) -> None:
    doc = {
        "actor_type": actor_type,
        "actor_id": actor_id,
        "action": action,
        "data": data,
        "created_at": now_utc(),
    }
    get_collection("audit_logs").insert_one(doc)


def parse_int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def chunked(iterable: Iterable[Any], size: int) -> Iterable[List[Any]]:
    chunk: List[Any] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
