# common_auth

Copy this package into other SafeCare services to get a consistent JWT contract that works with the auth-backend.

## Contents

- `jwt.py` – issue and verify JWT access tokens (`encode_jwt`, `verify_jwt`).
- `principal.py` – lightweight `Principal` dataclass used by authentication middleware.
- `middleware.py` – attaches the `principal` attribute to every Django request so downstream code can safely access it.
- `decorators.py` – helpers such as `require_auth`, `require_levels`, and `require_perm` that you can apply to function-based views.
- `errors.py` – common exception hierarchy (`AuthError`, `InvalidTokenError`, `ExpiredTokenError`, `InactiveUserError`).

## Integration steps for other services

1. Add a DRF/Django authentication class that reads the `Authorization: Bearer <token>` header first, then falls back to the `token` cookie. The class should call `common_auth.jwt.verify_jwt` with the shared `JWT_SECRET`, `JWT_ISSUER`, and `JWT_AUDIENCE` values and fetch the user payload from the auth service if needed.
2. Attach `common_auth.middleware.PrincipalMiddleware` so every request has a `request.principal` attribute. When authentication succeeds, populate `request.principal` with `common_auth.principal.Principal` so downstream handlers and decorators have full context (user id, level, groups, and permissions).
3. Use the decorators for quick permission checks, for example:

```python
from common_auth.decorators import require_auth, require_perm

@require_auth
@require_perm("sms.send")
def send_sms(request):
    ...
```

4. Surface consistent error codes by catching `common_auth.errors.AuthError` and mapping them to `HTTP 401/403` responses.

This kit keeps cookies + bearer headers compatible across `/auth`, `/sms`, `/shop`, `/laydi`, and `/core` so browser clients can continue reading `document.cookie` while services rely on Authorization headers.
