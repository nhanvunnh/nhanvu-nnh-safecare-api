from __future__ import annotations

from collections import OrderedDict

LEVEL_CUSTOMER = "Customer"
LEVEL_CASHIER = "Cashier"
LEVEL_MOD = "Mod"
LEVEL_ADMIN = "Admin"
LEVEL_ROOT = "Root"

LEVELS = [LEVEL_ROOT, LEVEL_ADMIN, LEVEL_MOD, LEVEL_CASHIER, LEVEL_CUSTOMER]
LEVEL_ORDER = OrderedDict(
    (
        (LEVEL_CUSTOMER, 0),
        (LEVEL_CASHIER, 1),
        (LEVEL_MOD, 2),
        (LEVEL_ADMIN, 3),
        (LEVEL_ROOT, 4),
    )
)

STATUS_ACTIVE = "Active"
STATUS_INACTIVE = "Inactive"
STATUS_BANNED = "Banned"
STATUS_PENDING = "Pending"
STATUSES = [STATUS_ACTIVE, STATUS_INACTIVE, STATUS_BANNED, STATUS_PENDING]

PERMISSION_CANONICAL = [
    "user.read",
    "user.list",
    "user.create",
    "user.update",
    "user.delete",
    "user.role.set",
    "group.read",
    "group.list",
    "group.create",
    "group.update",
    "group.delete",
    "group.perm.set",
    "auth.introspect",
]

DEFAULT_GROUPS = {
    "ROOT": {"description": "Root super administrators", "perms": ["*"]},
    "ADMIN": {
        "description": "Administrators",
        "perms": [
            "user.read",
            "user.list",
            "user.create",
            "user.update",
            "user.delete",
            "user.role.set",
            "group.read",
            "group.list",
            "group.create",
            "group.update",
            "group.delete",
            "group.perm.set",
        ],
    },
    "MOD": {
        "description": "Moderators",
        "perms": ["user.read", "user.list", "group.read", "group.list"],
    },
    "CASHIER": {
        "description": "Cashiers",
        "perms": ["user.read"],
    },
    "SELLER": {
        "description": "Sellers",
        "perms": ["user.read"],
    },
    "CUSTOMER": {
        "description": "Customers",
        "perms": [],
    },
}
