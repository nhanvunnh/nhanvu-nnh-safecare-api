def _scope_rank(scope):
    order = {"read": 1, "write": 2, "admin": 3}
    return order.get((scope or "").lower(), 0)


def has_scope(scope, required_scope):
    return _scope_rank(scope) >= _scope_rank(required_scope)
