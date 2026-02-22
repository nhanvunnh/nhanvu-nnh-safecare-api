# SafeCare Auth Service

Django 4 + DRF service that centralises authentication, RBAC, password resets, and social logins for the Server A stack. It runs behind `api.safecare.vn` with `BASE_PATH=/auth`, shares MongoDB with the other modules, and exposes both cookie + bearer token contracts so legacy web apps can continue reading `document.cookie` while new microservices rely on the `Authorization` header.

## Layout

```
auth-backend/
├── config/                 # Django project
├── auth_service/           # Domain logic (models, APIs, OAuth, RBAC)
├── common_auth/            # Copy-ready helpers for other services
├── management/commands/    # create_indexes, seed_defaults, create_default_admin
├── tests/                  # Django test suite (mongomock)
├── Dockerfile
├── docker-compose.yml      # Local dev (backend + mongo)
├── docker-compose.prod.yml # Used by services/auth/docker-compose.prod.yml
├── .env.example
└── README.md
```

## Environment variables

Copy `.env.example` to `.env` before running locally. Key settings:

| Variable | Description |
| --- | --- |
| `BASE_PATH` | Prefix enforced by Nginx Proxy Manager (`/auth`). |
| `MONGO_URI` / `MONGO_DB` | Auth database connection (auth-enabled Mongo). |
| `JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_ACCESS_MINUTES` | Access token contract. |
| `COOKIE_DOMAIN`, `COOKIE_SECURE`, `COOKIE_SAMESITE` | Browser cookie settings (`token` cookie is **not** HttpOnly by design). |
| `GOOGLE_CLIENT_ID/SECRET`, `MS_CLIENT_ID/SECRET/MS_TENANT` | OAuth credentials. |
| `EMAIL_*`, `PASSWORD_RESET_URL` | SMTP settings for forgot-password flow. |
| `RATE_LIMIT_LOGIN_PER_MINUTE`, `RATE_LIMIT_FORGOT_PER_HOUR` | Built-in throttling knobs. |
| `DEFAULT_ADMIN_*` | Optional bootstrap account (set `DEFAULT_ADMIN_ENABLED=1`). |

## Local development

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python manage.py create_indexes
docker compose exec backend python manage.py seed_defaults
docker compose exec backend python manage.py create_default_admin
curl http://localhost:8001/health
```

### Run `create_default_admin` manually in Docker

```bash
# Local compose (service: backend)
docker compose exec backend python manage.py create_default_admin

# Prod compose file (service: auth)
docker compose -f docker-compose.prod.yml exec auth python manage.py create_default_admin
```

The local compose stack exposes Django on `http://localhost:8001`. API URLs mirror production but without TLS, e.g. `http://localhost:8001/auth/v1/auth/login`.

## Deployment (Server A)

1. Sync this folder into `opt/apps/server-a/code/auth-backend` on the host.
2. Populate `opt/apps/server-a/services/auth/.env` with production secrets (template already committed).
3. Run `./deploy_service.sh auth` from `opt/apps/server-a/deploy`. The compose file builds from `../../code/auth-backend`, runs `create_indexes` + `seed_defaults` + `create_default_admin`, then starts Gunicorn on port 8000 attached to `proxy-network` + `infra-network`.
4. In Nginx Proxy Manager, add custom location `/auth` → `svc_auth:8000` with rewrite `^/auth/(.*)$ /$1 break;`.
5. Validate via `curl https://api.safecare.vn/auth/health`.

## API highlights

All endpoints live under `/auth` plus `/v1/...`.

```bash
# Register (defaults to CUSTOMER level)
curl -X POST https://api.safecare.vn/auth/v1/auth/register \
	-H "Content-Type: application/json" \
	-d '{"usernameType":"email","email":"demo@safecare.vn","password":"Pass123!","fullName":"Demo"}'

# Login (receives JSON token + Set-Cookie token)
curl -X POST https://api.safecare.vn/auth/v1/auth/login \
	-H "Content-Type: application/json" \
	-d '{"identifier":"demo@safecare.vn","password":"Pass123!"}'

# Self profile
curl -H "Authorization: Bearer <token>" https://api.safecare.vn/auth/v1/users/me

# Admin list (requires Mod+, perm user.list)
curl -H "Authorization: Bearer <admin-token>" https://api.safecare.vn/auth/v1/users?page=1&pageSize=20

# Group permissions
curl https://api.safecare.vn/auth/v1/groups/ADMIN/perms -H "Authorization: Bearer <admin-token>"

# Token introspection (perm auth.introspect)
curl -X POST https://api.safecare.vn/auth/v1/auth/introspect \
	-H "Authorization: Bearer <svc-token>" \
	-H "Content-Type: application/json" \
	-d '{"token":"<access-token>"}'
```

### RBAC model

- Levels (ascending): `Customer < Cashier < Mod < Admin < Root`. Root bypasses all checks.
- Default groups/perms seeded via `python manage.py seed_defaults`:
	- ROOT → `*`
	- ADMIN → `user.*` + `group.*`
	- MOD → read/list users & groups
	- CASHIER/SELLER/CUSTOMER → self-scope
- Service code computes `perms(user) = (groups perms ∪ extraPerms)` and ships the snapshot inside every JWT so downstream modules can short-circuit authorization.

### Password + email workflows

- Forgot password: rate-limited by IP+email, emits email containing `resetToken` link powered by `PASSWORD_RESET_URL`.
- Reset password: verifies hashed token, flips `used` flag, issues a fresh JWT + cookie.
- Change password: protected endpoint verifying the old password.

### OAuth (Google + Microsoft)

`/v1/oauth/<provider>/start` generates a state token (5-minute TTL) and redirects users to the provider consent page. `/v1/oauth/<provider>/callback` exchanges the code, verifies the ID token (PyJWK + RS256), links or creates the SafeCare user, issues the standard JWT cookie, and finally redirects to `OAUTH_REDIRECT_SUCCESS` (token also appended as a query param). Errors bounce to `OAUTH_REDIRECT_ERROR?error=<code>`.

## Common Auth kit

The reusable helpers live under [common_auth](common_auth). Copy this folder into any other Django/DRF service, then:

1. Use `common_auth.jwt.verify_jwt` to decode tokens with the shared secret.
2. Populate `request.principal` with `common_auth.principal.Principal` in your auth class.
3. Apply `common_auth.decorators.require_auth` / `require_perm` to views.
4. Consult [common_auth/README.md](common_auth/README.md) for integration notes.

## Tests

The suite uses `mongomock` and can run entirely in CI:

```
python manage.py test
```

Coverage includes cookie contracts, RBAC gates, introspection, and social linking logic.

## Troubleshooting

- `Unknown command: 'create_default_admin'`:
  - Container/image is still old and does not include the new command.
  - Rebuild and restart, then retry:

```bash
# local compose
docker compose down
docker compose up --build -d

# prod compose
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up --build -d
```
