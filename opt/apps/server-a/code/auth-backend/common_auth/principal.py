from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Principal:
    user_id: str
    level: str
    status: str
    groups: list[str] = field(default_factory=list)
    perms: set[str] = field(default_factory=set)
    token: str | None = None

    @property
    def is_authenticated(self) -> bool:
        return True

    def has_perm(self, perm: str) -> bool:
        return perm in self.perms

    def has_any_perm(self, perm_list: Iterable[str]) -> bool:
        return any(self.has_perm(perm) for perm in perm_list)
