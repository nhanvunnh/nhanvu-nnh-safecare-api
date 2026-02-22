# Service URL Mapping For Split-Server Deployment

Tai lieu nay quy dinh cach set cac bien URL lien service khi tach he thong thanh nhieu server.

## 1) Nguyen tac chung

- Moi service chi goi service khac qua bien moi truong (`*_SERVICE_URL`, `*_BASE_URL`, `AUTH_SERVICE_URL`).
- Khong hard-code `svc_*` trong code.
- Moi truong local Docker van co the dung DNS container (`svc_auth`, `svc_image`, ...).
- Moi truong split-server dung URL private (VPC/LAN) hoac public API gateway.

## 2) Bien can set theo module

### 2.1 GNH (`services/gnh/.env`)

- `AUTH_SERVICE_URL`
- `AUTH_API_VERIFY_URL` (optional override)
- `IMAGE_SERVICE_URL`
- `SHEET_SYNC_SERVICE_URL`
- `SHEET_SYNC_BASE_URL` (giu de tuong thich)
- `IMAGE_SERVICE_BASE_URL` (giu de tuong thich)

Khuyen nghi:
- Set `AUTH_SERVICE_URL`, `IMAGE_SERVICE_URL`, `SHEET_SYNC_SERVICE_URL` la chinh.
- De `*_BASE_URL` bang cung gia tri de dong bo migration.

### 2.2 Sheet Sync (`services/sheet-sync/.env`)

- `AUTH_SERVICE_URL`
- `AUTH_API_VERIFY_URL` (optional override)

## 3) Mapping theo kieu ha tang

### 3.1 Monolith Docker (1 host, 1 compose)

```env
AUTH_SERVICE_URL=http://svc_auth:8000
IMAGE_SERVICE_URL=http://svc_image:8000
SHEET_SYNC_SERVICE_URL=http://svc_sheet_sync:8000/sheet
```

### 3.2 Tach server noi bo (private network)

Vi du:
- auth o `10.10.1.11:8000`
- image o `10.10.1.12:8000`
- sheet-sync o `10.10.1.13:8000`

`services/gnh/.env`:
```env
AUTH_SERVICE_URL=http://10.10.1.11:8000
AUTH_API_VERIFY_URL=http://10.10.1.11:8000/auth/v1/auth/api-tokens/verify
IMAGE_SERVICE_URL=http://10.10.1.12:8000
IMAGE_SERVICE_BASE_URL=http://10.10.1.12:8000
SHEET_SYNC_SERVICE_URL=http://10.10.1.13:8000/sheet
SHEET_SYNC_BASE_URL=http://10.10.1.13:8000/sheet
```

`services/sheet-sync/.env`:
```env
AUTH_SERVICE_URL=http://10.10.1.11:8000
AUTH_API_VERIFY_URL=http://10.10.1.11:8000/auth/v1/auth/api-tokens/verify
```

### 3.3 Tach server qua domain n?i b?/public

Vi du:
- auth: `https://auth.internal.safecare.vn`
- image: `https://image.internal.safecare.vn`
- sheet: `https://sheet.internal.safecare.vn`

`services/gnh/.env`:
```env
AUTH_SERVICE_URL=https://auth.internal.safecare.vn
AUTH_API_VERIFY_URL=https://auth.internal.safecare.vn/auth/v1/auth/api-tokens/verify
IMAGE_SERVICE_URL=https://image.internal.safecare.vn
IMAGE_SERVICE_BASE_URL=https://image.internal.safecare.vn
SHEET_SYNC_SERVICE_URL=https://sheet.internal.safecare.vn/sheet
SHEET_SYNC_BASE_URL=https://sheet.internal.safecare.vn/sheet
```

`services/sheet-sync/.env`:
```env
AUTH_SERVICE_URL=https://auth.internal.safecare.vn
AUTH_API_VERIFY_URL=https://auth.internal.safecare.vn/auth/v1/auth/api-tokens/verify
```

## 4) Checklist khi doi URL

1. Cap nhat `.env` cua service.
2. Redeploy service:
- `auth` (neu doi verify endpoint auth)
- `sheet-sync`
- `gnh`
3. Kiem tra health:
- `/auth/health`
- `/sheet/health`
- `/gnh/health`
4. Kiem tra verify token:
- `POST /auth/v1/auth/api-tokens/verify`
5. Kiem tra API nghiep vu:
- `POST /gnh/gets`
- `POST /gnh/sync`

## 5) Lua chon fallback khi auth tam loi

- `AUTH_API_VERIFY_FALLBACK_LOCAL=1`: cho phep fallback local collection.
- `AUTH_API_VERIFY_FALLBACK_LOCAL=0`: bat buoc verify qua auth service (strict mode).

Khuyen nghi:
- Production split-server: dat `0` sau khi he thong on dinh.
- Giai doan migration: dat `1` de tranh downtime.
