# Sheet Sync Backend (server-a)

Service dong bo Google Sheet dung chung cho nhieu module.

## Base URL
- Production: `https://api.safecare.vn/sheet`
- Noi bo container: `http://svc_sheet_sync:8000/sheet`
- Health public: `GET /sheet/health`
- Health noi bo: `GET /health`

## Auth
- `api_token` (scope `read`/`write`/`admin`) trong body, hoac
- `service_token` (danh cho service noi bo, vd `gnh`)
- `api_token` duoc verify qua auth service endpoint `/auth/v1/auth/api-tokens/verify`.
- Fallback local token chi dung khi auth service khong san sang (theo env `AUTH_API_VERIFY_FALLBACK_LOCAL`).

## Bien URL lien service
- `AUTH_SERVICE_URL` (vd `http://svc_auth:8000`)
- `AUTH_API_VERIFY_URL` (override endpoint verify, neu can)
- `AUTH_API_VERIFY_HOST` (Host header khi goi verify; nen dat `api.safecare.vn` neu host noi bo co dau `_`)

## Tao va lay `api_token` (qua auth service)

`sheet-sync` khong tu tao token. Token duoc quan ly tap trung o `auth` module.

Base URL auth (prod): `https://api.safecare.vn/auth`

### 1) Dang nhap admin de lay JWT

- `POST /auth/v1/auth/login`

Request:
```json
{
  "identifier": "admin@safecare.vn",
  "password": "your-admin-password"
}
```

Response:
```json
{
  "ok": true,
  "user": {
    "id": "65f0b2...",
    "level": "Admin"
  },
  "token": "eyJhbGciOi..."
}
```

Lay JWT tu truong `token` de goi cac API tao/list token ben duoi.

### 2) Tao `api_token` cho sheet-sync

- `POST /auth/v1/api-tokens`
- Header: `Authorization: Bearer <JWT_ADMIN>`

Request (auto-generate token):
```json
{
  "name": "sheet-sync-write",
  "scope": "write",
  "note": "for sheet sync jobs",
  "expiresDays": 180
}
```

Response:
```json
{
  "ok": true,
  "token": {
    "id": "65f1aa...",
    "name": "sheet-sync-write",
    "scope": "write",
    "isActive": true,
    "expiresAt": "2026-08-20T08:00:00+00:00",
    "token": "mXx...plain-token...9kQ",
    "tokenPreview": "mXx...9kQ"
  }
}
```

Luu y: gia tri `token` plain chi nen copy ngay luc tao.

### 3) Lay danh sach `api_token`

- `GET /auth/v1/api-tokens?page=1&pageSize=20&scope=write`
- Header: `Authorization: Bearer <JWT_ADMIN>`

Response:
```json
{
  "ok": true,
  "data": [
    {
      "id": "65f1aa...",
      "name": "sheet-sync-write",
      "scope": "write",
      "isActive": true,
      "tokenPreview": "mXx...9kQ",
      "expiresAt": "2026-08-20T08:00:00+00:00"
    }
  ],
  "page": 1,
  "pageSize": 20,
  "total": 1
}
```

### 4) Lay chi tiet 1 token

- `GET /auth/v1/api-tokens/{token_id}`
- Header: `Authorization: Bearer <JWT_ADMIN>`

Response:
```json
{
  "ok": true,
  "token": {
    "id": "65f1aa...",
    "name": "sheet-sync-write",
    "scope": "write",
    "isActive": true,
    "tokenPreview": "mXx...9kQ",
    "createdAt": "2026-02-21T08:10:00+00:00"
  }
}
```

### 5) Verify token (de test nhanh)

- `POST /auth/v1/auth/api-tokens/verify`

Request:
```json
{
  "token": "mXx...plain-token...9kQ",
  "requiredScope": "write"
}
```

Response hop le:
```json
{
  "ok": true,
  "active": true,
  "scope": "write",
  "name": "sheet-sync-write",
  "expiresAt": "2026-08-20T08:00:00+00:00"
}
```

Response khong hop le:
```json
{
  "ok": true,
  "active": false
}
```

### 6) Dung token vua tao goi API sheet-sync

Vi du chay sync job:
```json
{
  "api_token": "mXx...plain-token...9kQ",
  "app_code": "gnh",
  "direction": "manual"
}
```

## Quy trinh hoat dong
1. App nghiep vu (vi du `gnh`) ghi du lieu vao Mongo DB rieng cua app.
2. App goi `sheet-sync` qua API `/sheet/jobs/run` voi `app_code`.
3. `sheet-sync` doc cau hinh `app_code` (sheet/worksheet/collection/key field).
4. Engine sync chay 2 chieu:
- Sheet -> DB: them/cap nhat ban ghi moi hon.
- DB -> Sheet: update/append dong moi hon.
5. Ket qua sync duoc ghi vao `sheet_sync_job_logs`.
6. App nghiep vu doc log qua `/sheet/logs/list` (hoac expose lai qua API rieng cua app).

## Nhiem vu tung API
1. `POST /sheet/apps/upsert`
- Tao/cap nhat cau hinh dong bo cho 1 `app_code`.
- Dung khi onboard app moi (gnh/order/ticket...).
- Scope: `admin`.

2. `POST /sheet/apps/get`
- Lay chi tiet cau hinh dong bo cua 1 `app_code`.
- Dung de kiem tra mapping truoc khi chay sync.
- Scope: `read`.

3. `POST /sheet/apps/list`
- Liet ke tat ca app da dang ky dong bo.
- Dung cho man hinh quan tri va kiem tra cau hinh.
- Scope: `read`.

4. `POST /sheet/jobs/run`
- Chay sync ngay cho 1 `app_code`.
- Ho tro `delete_key` de xoa key tren Sheet truoc khi sync lai.
- Day la API thuc thi chinh cua service.
- Scope: `write` hoac `service_token` noi bo.

5. `POST /sheet/logs/list`
- Lay danh sach logs dong bo theo `app_code`/`status`, co phan trang.
- Dung de giam sat van hanh va truy vet loi.
- Scope: `read` hoac `service_token`.

## API details

### 1) Upsert app config
- `POST /sheet/apps/upsert`
- Scope: `admin`

Request:
```json
{
  "api_token": "sheet_admin_token_xxx",
  "app_code": "gnh",
  "name": "Giao Nhan Hang",
  "sheet_name": "NVC-GIAONHANHANG",
  "worksheet_name": "GNH",
  "target_db": "db_gnh",
  "target_collection": "gnh_sheet",
  "key_field": "MA_GIAO_NHAN",
  "updated_at_field": "UPDATED_AT",
  "date_format": "%d/%m/%Y %H:%M:%S",
  "fields": [
    "MA_GIAO_NHAN",
    "TEN_KHACH_HANG",
    "SO_DIEN_THOAI",
    "MA_CAN_HO",
    "THU_HOI",
    "MA_GIAO_HANG",
    "MA_KHO",
    "VI_TRI",
    "NGAY_NHAN",
    "NGAY_GIAO",
    "GIA_TIEN",
    "HINH_NHAN",
    "HINH_GIAO",
    "NOI_DUNG_GOI_HANG",
    "GIAO_HANG",
    "TINH_TRANG",
    "GIO_NHAN",
    "GIO_GIAO",
    "GHI_CHU",
    "LOAI_VE",
    "HTTT",
    "UPDATED_AT"
  ],
  "is_active": true
}
```

Response:
```json
{
  "ok": true,
  "data": {
    "app_code": "gnh",
    "name": "Giao Nhan Hang",
    "sheet_name": "NVC-GIAONHANHANG",
    "worksheet_name": "GNH",
    "target_db": "db_gnh",
    "target_collection": "gnh_sheet",
    "key_field": "MA_GIAO_NHAN",
    "updated_at_field": "UPDATED_AT",
    "date_format": "%d/%m/%Y %H:%M:%S",
    "fields": ["MA_GIAO_NHAN", "TEN_KHACH_HANG", "UPDATED_AT"],
    "is_active": true
  }
}
```

### 2) Get app config
- `POST /sheet/apps/get`
- Scope: `read`

Request:
```json
{
  "api_token": "sheet_read_token_xxx",
  "app_code": "gnh"
}
```

Response:
```json
{
  "ok": true,
  "data": {
    "app_code": "gnh",
    "name": "Giao Nhan Hang",
    "sheet_name": "NVC-GIAONHANHANG",
    "worksheet_name": "GNH",
    "target_db": "db_gnh",
    "target_collection": "gnh_sheet",
    "key_field": "MA_GIAO_NHAN",
    "updated_at_field": "UPDATED_AT",
    "date_format": "%d/%m/%Y %H:%M:%S",
    "fields": ["MA_GIAO_NHAN", "TEN_KHACH_HANG", "UPDATED_AT"],
    "is_active": true
  }
}
```

### 3) List app configs
- `POST /sheet/apps/list`
- Scope: `read`

Request:
```json
{
  "api_token": "sheet_read_token_xxx"
}
```

Response:
```json
{
  "ok": true,
  "data": [
    {
      "app_code": "gnh",
      "name": "Giao Nhan Hang",
      "is_active": true
    }
  ]
}
```

### 4) Run sync job
- `POST /sheet/jobs/run`
- Scope: `write` (hoac `service_token`)

Request (manual sync):
```json
{
  "service_token": "change-me-internal-token",
  "app_code": "gnh",
  "direction": "manual"
}
```

Request (delete key tren sheet roi sync):
```json
{
  "service_token": "change-me-internal-token",
  "app_code": "gnh",
  "direction": "manual",
  "delete_key": "GNH-20260221-0002"
}
```

Response:
```json
{
  "ok": true,
  "inserted_db": 2,
  "updated_db": 1,
  "updated_sheet": 3,
  "appended_sheet": 0
}
```

### 5) List sync logs
- `POST /sheet/logs/list`
- Scope: `read` (hoac `service_token`)

Request:
```json
{
  "service_token": "change-me-internal-token",
  "app_code": "gnh",
  "status": "success",
  "page": 1,
  "page_size": 20
}
```

Response:
```json
{
  "ok": true,
  "data": [
    {
      "timeCreate": "21/02/2026 11:20:11",
      "app_code": "gnh",
      "direction": "manual",
      "status": "success",
      "message": "db_insert=0 db_update=1 sheet_update=1 sheet_append=0",
      "stats": {
        "inserted_db": 0,
        "updated_db": 1,
        "updated_sheet": 1,
        "appended_sheet": 0
      }
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1,
  "total_pages": 1,
  "page_numbers": [1],
  "show_first": false,
  "show_last": false,
  "show_left_ellipsis": false,
  "show_right_ellipsis": false
}
```

## Error samples
- Unauthorized:
```json
{"Error":"Unauthorized"}
```
- Missing app_code:
```json
{"Error":"Missing app_code"}
```
- Inactive or missing config:
```json
{"Error":"App config not found or inactive"}
```

## Bootstrap
```bash
python manage.py create_indexes
python manage.py seed_defaults
```

`seed_defaults` tao app config mac dinh cho `gnh`.
