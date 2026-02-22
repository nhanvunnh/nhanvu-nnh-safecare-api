# GNH Backend (server-a)

Dich vu API GNH theo cau truc server-a.

## Base URL
- Production: `https://api.safecare.vn/gnh`
- Noi bo container: `http://svc_gnh:8000/gnh`
- Health public: `GET /gnh/health`
- Health noi bo: `GET /health`

`BASE_PATH` mac dinh la `/gnh`, vi vay endpoint thuc te co dang `/gnh/...`.

## Auth
- Ho tro `api_token` (scope `read`/`write`/`admin`) trong body.
  - `gnh` verify `api_token` qua auth service endpoint `/auth/v1/auth/api-tokens/verify`.
  - Fallback local token chi dung khi auth service khong san sang (theo env `AUTH_API_VERIFY_FALLBACK_LOCAL`).
- Fallback token nguoi dung qua truong `token` (JWT) trong body.

## Bien URL lien service
- `AUTH_SERVICE_URL` (vd `http://svc_auth:8000`)
- `AUTH_API_VERIFY_URL` (override endpoint verify, neu can)
- `IMAGE_SERVICE_URL` (vd `http://svc_image:8000`)
- `SHEET_SYNC_SERVICE_URL` (vd `http://svc_sheet_sync:8000/sheet`)
- `SHEET_SYNC_BASE_URL` / `IMAGE_SERVICE_BASE_URL` duoc giu de tuong thich nguoc.

## Field GNH
- `MA_GIAO_NHAN`, `TEN_KHACH_HANG`, `SO_DIEN_THOAI`, `MA_CAN_HO`, `THU_HOI`, `MA_GIAO_HANG`, `MA_KHO`, `VI_TRI`, `NGAY_NHAN`, `NGAY_GIAO`, `GIA_TIEN`, `HINH_NHAN`, `HINH_GIAO`, `NOI_DUNG_GOI_HANG`, `GIAO_HANG`, `TINH_TRANG`, `GIO_NHAN`, `GIO_GIAO`, `GHI_CHU`, `LOAI_VE`, `HTTT`, `UPDATED_AT`

## Endpoints

### 1) Danh sach
- `POST /gnh/gets`
- Scope: `read`

Request:
```json
{
  "api_token": "gnh_read_token_xxx",
  "page": 1,
  "page_size": 20,
  "phone_filter": "0909123456"
}
```

Response:
```json
{
  "ok": true,
  "data": [
    {
      "MA_GIAO_NHAN": "GNH-20260221-0001",
      "TEN_KHACH_HANG": "Nguyen Van A",
      "SO_DIEN_THOAI": "0909123456",
      "MA_CAN_HO": "A1-1208",
      "THU_HOI": "",
      "MA_GIAO_HANG": "DH123456",
      "MA_KHO": "K1",
      "VI_TRI": "Locker 5",
      "NGAY_NHAN": "21/02/2026",
      "NGAY_GIAO": "",
      "GIA_TIEN": "150000",
      "HINH_NHAN": "http://svc_image:8000/get_image?file=GNH_Images%2Fabc.jpg",
      "HINH_GIAO": "",
      "NOI_DUNG_GOI_HANG": "Tai lieu",
      "GIAO_HANG": "FALSE",
      "TINH_TRANG": "FALSE",
      "GIO_NHAN": "10:35:00",
      "GIO_GIAO": "",
      "GHI_CHU": "Nhan tai le tan",
      "LOAI_VE": "Vang lai",
      "HTTT": "CK",
      "UPDATED_AT": "21/02/2026 10:36:12"
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

### 2) Chi tiet
- `POST /gnh/get`
- Scope: `read`

Request:
```json
{
  "api_token": "gnh_read_token_xxx",
  "key": "GNH-20260221-0001"
}
```

Response:
```json
{
  "ok": true,
  "data": {
    "MA_GIAO_NHAN": "GNH-20260221-0001",
    "TEN_KHACH_HANG": "Nguyen Van A",
    "UPDATED_AT": "21/02/2026 10:36:12"
  }
}
```

### 3) Tao moi
- `POST /gnh/create`
- Scope: `write`

Request:
```json
{
  "api_token": "gnh_write_token_xxx",
  "MA_GIAO_NHAN": "GNH-20260221-0002",
  "TEN_KHACH_HANG": "Tran Thi B",
  "SO_DIEN_THOAI": "0988777666",
  "MA_CAN_HO": "B2-0901",
  "THU_HOI": "",
  "MA_GIAO_HANG": "DH789001",
  "MA_KHO": "K2",
  "VI_TRI": "Desk 2",
  "NGAY_NHAN": "21/02/2026",
  "NGAY_GIAO": "",
  "GIA_TIEN": "200000",
  "HINH_NHAN": "GNH_Images/xyz.jpg",
  "HINH_GIAO": "",
  "NOI_DUNG_GOI_HANG": "My pham",
  "GIAO_HANG": "FALSE",
  "TINH_TRANG": "FALSE",
  "GIO_NHAN": "11:00:00",
  "GIO_GIAO": "",
  "GHI_CHU": "",
  "LOAI_VE": "Ve thang",
  "HTTT": "Tien mat"
}
```

Response:
```json
{
  "ok": true,
  "data": {
    "MA_GIAO_NHAN": "GNH-20260221-0002",
    "UPDATED_AT": "21/02/2026 11:00:32"
  },
  "sync": {
    "ok": true,
    "inserted_db": 0,
    "updated_db": 0,
    "updated_sheet": 0,
    "appended_sheet": 1
  }
}
```

### 4) Cap nhat
- `POST /gnh/update`
- Scope: `write`

Request:
```json
{
  "api_token": "gnh_write_token_xxx",
  "MA_GIAO_NHAN": "GNH-20260221-0002",
  "TINH_TRANG": "TRUE",
  "GIAO_HANG": "TRUE",
  "NGAY_GIAO": "21/02/2026",
  "GIO_GIAO": "14:10:00",
  "GHI_CHU": "Da giao tan tay"
}
```

Response:
```json
{
  "ok": true,
  "data": {
    "MA_GIAO_NHAN": "GNH-20260221-0002",
    "TINH_TRANG": "TRUE",
    "GIAO_HANG": "TRUE"
  },
  "sync": {
    "ok": true,
    "inserted_db": 0,
    "updated_db": 0,
    "updated_sheet": 1,
    "appended_sheet": 0
  }
}
```

### 5) Xoa
- `POST /gnh/delete`
- Scope: `write`

Request:
```json
{
  "api_token": "gnh_write_token_xxx",
  "MA_GIAO_NHAN": "GNH-20260221-0002"
}
```

Response:
```json
{
  "ok": true,
  "deleted": "GNH-20260221-0002",
  "sheet_delete": {
    "ok": true,
    "deleted_rows": 1
  },
  "sync": {
    "ok": true,
    "inserted_db": 0,
    "updated_db": 0,
    "updated_sheet": 0,
    "appended_sheet": 0
  }
}
```

### 6) Sync thu cong
- `POST /gnh/sync`
- Scope: `write`

Request:
```json
{
  "api_token": "gnh_write_token_xxx"
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

### 7) Logs sync
- `POST /gnh/logs`
- Scope: `read`

Request:
```json
{
  "api_token": "gnh_read_token_xxx",
  "page": 1,
  "page_size": 20,
  "status": "success"
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

## Loi thuong gap
- Unauthorized:
```json
{"Error":"Unauthorized"}
```
- Missing key:
```json
{"Error":"Missing MA_GIAO_NHAN"}
```
- Not found:
```json
{"Error":"Not found"}
```

## Google Sheet Sync
- GNH goi service `sheet-sync` qua API de dong bo.
- Manual sync qua endpoint `/gnh/sync` (se trigger `/sheet/jobs/run` voi `app_code=gnh`).
- Logs dong bo qua `/gnh/logs` (doc tu `sheet-sync`, fallback local logs neu service khong san sang).

## Image integration
- Truong anh (`HINH_NHAN`, `HINH_GIAO`) duoc map sang URL image service:
  - `${IMAGE_SERVICE_BASE_URL}/get_image?file=<path>`

## Bootstrap
- Tao index:
  - `python manage.py create_indexes`
