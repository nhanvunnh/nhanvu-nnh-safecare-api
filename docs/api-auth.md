# Auth Module API (auth-backend)

Backend URL cố định:

- Dev: `http://192.168.1.5:8090`
- Prod: `https://api.safecare.vn`

Base path production (theo `BASE_PATH`): `/auth`

Ngoài ra còn có healthcheck không prefix: `GET /health`.

## Authentication

- Hầu hết endpoint `v1/*` yêu cầu đăng nhập: gửi `Authorization: Bearer <JWT>` **hoặc** dùng cookie `token` (được set khi login/register/reset).
- Các endpoint `AllowAny`: register/login/logout/forgot-password/reset-password và OAuth start/callback.

## Health

- `GET /health` → `200 {"status":"ok"}`
- `GET /auth/health` → `200 {"status":"ok"}`

## Auth (v1)

### Register

- `POST /auth/v1/auth/register`
- Body
  - `usernameType`: `"email"` | `"phone"`
  - `email` (required nếu `usernameType=email`)
  - `phone` (required nếu `usernameType=phone`)
  - `password` (min 8)
  - `fullName`
- Response `200`
  - `{"ok": true, "user": <User>, "token": "<jwt>"}`

### Login

- `POST /auth/v1/auth/login`
- Body: `{"identifier": "<email|phone>", "password": "..." }`
- Response `200`: `{"ok": true, "user": <User>, "token": "<jwt>"}`
- Lỗi thường gặp
  - `401 {"ok": false, "error": "Invalid credentials"}`
  - `403 {"ok": false, "error": "Account disabled"}`
  - `429 {"ok": false, "error": "Too many attempts"}`

### Logout

- `POST /auth/v1/auth/logout`
- Response `200`: `{"ok": true}` (xóa cookie token)

### Forgot password

- `POST /auth/v1/auth/forgot-password`
- Body: `{"email":"..."}`
- Response `200`: luôn trả `{"ok": true, "message": "If email exists, we sent instructions."}`

### Reset password

- `POST /auth/v1/auth/reset-password`
- Body: `{"resetToken":"...", "newPassword":"..." }`
- Response `200`: `{"ok": true, "token":"<jwt>", "user": <User>}`
- Lỗi: `400 {"ok": false, "error": "Invalid reset token"}`

### Change password

- `POST /auth/v1/auth/change-password` (require auth)
- Body: `{"oldPassword":"...", "newPassword":"..." }`
- Response `200`: `{"ok": true}`
- Lỗi: `400 {"ok": false, "error": "Invalid password"}`

### Introspect token

- `POST /auth/v1/auth/introspect` (require auth + permission `auth.introspect`)
- Body: `{"token":"<jwt>" }`
- Response:
  - Nếu verify fail: `{"active": false}`
  - Nếu ok: `{"active": true, "sub": "...", "level": "...", "status": "...", "groups": [...], "perms": [...], "exp": <unix>}`

## Users (v1)

### Me

- `GET /auth/v1/users/me` (require auth)
  - Response: `{"ok": true, "user": <User + perms>, "perms": ["..."]}`
- `PATCH /auth/v1/users/me` (require auth)
  - Body (ít nhất 1 field): `fullName`, `email`, `phone`
  - Response: `{"ok": true, "user": <User>}`

### Collection

- `GET /auth/v1/users` (require auth + level ≥ `Mod` + perm `user.list`)
  - Query: `q`, `level`, `status`, `page` (default 1), `pageSize` (default 20, max 100)
  - Response: `{"ok": true, "data": [<User>], "page": 1, "pageSize": 20, "total": 123}`
- `POST /auth/v1/users` (require auth + perm `user.create`)
  - Body: `email?`, `phone?`, `password`, `fullName`, `level?`, `status?`, `groups?[]`, `extraPerms?[]`
  - Response: `{"ok": true, "user": <User>}`

### Detail

- `GET /auth/v1/users/{user_id}` (perm `user.read`)
- `PATCH /auth/v1/users/{user_id}` (perm `user.update`)
  - Body (partial): `email`, `phone`, `fullName`, `level`, `status`, `groups`, `extraPerms`
- `POST /auth/v1/users/{user_id}/ban` (perm `user.update`)
- `POST /auth/v1/users/{user_id}/activate` (perm `user.update`)
- `POST /auth/v1/users/{user_id}/set-level` (perm `user.role.set`)
  - Body: `{"level":"Customer|Cashier|Mod|Admin|Root"}`
- `POST /auth/v1/users/{user_id}/groups` (require level ≥ `Admin` + perm `user.update`)
  - Body: `{"groups":["ADMIN","MOD", ...]}`

Ghi chú: User `Root` chỉ có thể bị chỉnh bởi principal level `Root`.

## Groups (v1)

- `GET /auth/v1/groups` (perm `group.list`) → `{"ok": true, "data": [...] }`
- `POST /auth/v1/groups` (perm `group.create`)
  - Body: `{"code":"ADMIN","name":"Administrators","description?":"...","status?":"Active|Inactive"}`
- `GET /auth/v1/groups/{code}` (perm `group.read`) → kèm `perms`
- `PATCH /auth/v1/groups/{code}` (perm `group.update`)
- `DELETE /auth/v1/groups/{code}` (perm `group.delete`)
- `GET /auth/v1/groups/{code}/perms` (perm `group.read`)
- `POST /auth/v1/groups/{code}/perms` (perm `group.perm.set`)
  - Body: `{"permsAdd":["user.read"], "permsRemove":["user.delete"]}`

## OAuth (v1)

- `GET /auth/v1/oauth/google/start?redirect=<url>` → redirect sang Google
- `GET /auth/v1/oauth/google/callback?state=...&code=...` → redirect về `OAUTH_REDIRECT_SUCCESS` (append `token=...`) và set cookie
- `GET /auth/v1/oauth/microsoft/start?redirect=<url>`
- `GET /auth/v1/oauth/microsoft/callback?state=...&code=...`

## Legacy

- `POST /auth/user/login` (giống `v1/auth/login`)
- `POST /auth/user/register` (giống `v1/auth/register`)

## User object

`<User>` (trả về từ API) có dạng:

```json
{
  "id": "…",
  "email": "…",
  "phone": "…",
  "fullName": "…",
  "level": "Customer|Cashier|Mod|Admin|Root",
  "status": "Active|Inactive|Banned|Pending",
  "groups": ["ADMIN"],
  "extraPerms": ["user.read"],
  "verifiedEmail": false,
  "verifiedPhone": false,
  "lastLoginAt": "2026-02-19T00:00:00Z",
  "createdAt": "…",
  "updatedAt": "…"
}
```

## API Tokens (v1)

Cac API nay dung cho quan tri token ky thuat. Yeu cau user dang nhap co level `Admin` tro len.

- `GET /auth/v1/api-tokens`
  - Query:
    - `page` (default 1), `pageSize` (default 20, max 100)
    - `scope` (optional): `read|write|admin`
    - `isActive` (optional): `true|false`
  - Response: `{"ok": true, "data": [...], "page": 1, "pageSize": 20, "total": 10}`

- `POST /auth/v1/api-tokens`
  - Body:
    - `name` (required)
    - `scope` (optional): `read|write|admin`, default `read`
    - `note` (optional)
    - `expiresDays` (optional, int > 0)
    - `token` (optional, neu bo qua se auto-generate)
  - Response:
    - `201 {"ok": true, "token": {..., "token": "<plain-token>"}}`
  - Luu y: plain token chi nen copy ngay luc tao.

- `GET /auth/v1/api-tokens/{token_id}`
  - Response: `{"ok": true, "token": {...}}`

- `PATCH /auth/v1/api-tokens/{token_id}`
  - Body (partial):
    - `name`, `scope`, `note`, `isActive`, `expiresAt`
  - Response: `{"ok": true, "token": {...}}`

- `POST /auth/v1/api-tokens/{token_id}/toggle`
  - Response: `{"ok": true, "token": {...}}`

- `DELETE /auth/v1/api-tokens/{token_id}`
  - Response: `{"ok": true}`

### API token verify (for service-to-service)

- `POST /auth/v1/auth/api-tokens/verify` (AllowAny)
- Body:
  - `token` (required)
  - `requiredScope` (optional): `read|write|admin`, default `read`
- Response:
  - Invalid/inactive/expired/insufficient scope: `{"ok": true, "active": false}`
  - Valid: `{"ok": true, "active": true, "scope": "write", "name": "gnh-internal", "expiresAt": null}`
