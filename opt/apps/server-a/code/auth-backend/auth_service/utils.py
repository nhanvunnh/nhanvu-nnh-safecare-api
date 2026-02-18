from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    cleaned = email.strip().lower()
    return cleaned or None


VN_PREFIX = "+84"
VN_LEADING_ZERO = "0"


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    if digits.startswith("84"):
        local = digits[2:]
    elif digits.startswith("0"):
        local = digits[1:]
    else:
        local = digits
    return f"{VN_PREFIX}{local}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
