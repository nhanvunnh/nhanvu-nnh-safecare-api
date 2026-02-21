# Deploy GNH Service (`/gnh`) on Windows Local and Ubuntu Prod

Tai lieu nay huong dan trien khai service `gnh` (container `svc_gnh`) theo dung cau truc `server-a` da co.

## 1) Pham vi

Service GNH cung cap:
- `GET /gnh/health`
- `POST /gnh/gets`
- `POST /gnh/get`
- `POST /gnh/create`
- `POST /gnh/update`
- `POST /gnh/delete`
- `POST /gnh/sync`
- `POST /gnh/logs`

Luu y: GNH hien tai goi service trung gian `sheet-sync` de thuc hien dong bo Google Sheet.

## 2) Files lien quan

- Code service: `opt/apps/server-a/code/gnh-backend`
- Compose rieng service: `opt/apps/server-a/services/gnh/docker-compose.prod.yml`
- Env service: `opt/apps/server-a/services/gnh/.env`
- Secret Google SA:
  - Host path: `opt/apps/server-a/services/gnh/secrets/safedatabase-a88bf902aa78.json`
  - Container path: `/run/secrets/safedatabase-a88bf902aa78.json`
- Compose tong: `opt/apps/server-a/services/docker-compose.prod.yml`
- Compose sheet-sync: `opt/apps/server-a/services/sheet-sync/docker-compose.prod.yml`
- Script deploy: `opt/apps/server-a/deploy/deploy_service.ps1`, `opt/apps/server-a/deploy/deploy_service.sh`
- Mongo init users: `opt/apps/server-a/infra/mongo_init/create_app_users.js`
- Infra env: `opt/apps/server-a/infra/.env.infra`

## 3) Chuan bi chung

1. Cap nhat env infra co mat khau DB GNH:
- File: `opt/apps/server-a/infra/.env.infra`
- Dam bao co bien:
```env
GNH_DB_PASS=gnh-strong-pass
```

2. Cap nhat env service GNH:
- File: `opt/apps/server-a/services/gnh/.env`
- Kiem tra cac bien quan trong:
```env
BASE_PATH=/gnh
MONGO_URI=mongodb://gnh_user:gnh-strong-pass@shared_mongo:27017/db_gnh?authSource=db_gnh
MONGO_DB=db_gnh
GOOGLE_SERVICE_ACCOUNT_FILE=/run/secrets/safedatabase-a88bf902aa78.json
IMAGE_SERVICE_BASE_URL=http://svc_image:8000
SHEET_SYNC_ENABLED=1
SHEET_SYNC_BASE_URL=http://svc_sheet_sync:8000/sheet
SHEET_SYNC_SERVICE_TOKEN=change-me-internal-token
```

Gia tri `SHEET_SYNC_SERVICE_TOKEN` phai giong `INTERNAL_SERVICE_TOKEN` trong `services/sheet-sync/.env`.

3. Dat file service-account JSON:
- Tao file:
  - `opt/apps/server-a/services/gnh/secrets/safedatabase-a88bf902aa78.json`

4. Dam bao networks ton tai:
- `proxy-network`
- `infra-network`

## 4) Deploy tren Windows local

Chay tu root repo `E:\CodeAd2026\nhanvu-nnh-safecare-api`.

### 4.1 Re-apply infra (neu moi them `GNH_DB_PASS`)

```powershell
Set-Location .\opt\apps\server-a\deploy
.\deploy_infra.ps1
```

Neu khong co `deploy_infra.ps1`, chay tay:

```powershell
Set-Location ..\infra
docker compose -f docker-compose.infra.yml up -d
```

### 4.2 Deploy image service (phu thuoc de render anh)

```powershell
Set-Location ..\deploy
.\deploy_service.ps1 image
```

### 4.3 Deploy gnh service

```powershell
.\deploy_service.ps1 sheet-sync
.\deploy_service.ps1 gnh
```

### 4.4 Kiem tra nhanh

```powershell
docker ps | findstr svc_gnh
docker logs --tail 200 svc_gnh
curl http://localhost:8000/health
```

Goi qua domain/NPM route:

```powershell
curl https://api.safecare.vn/gnh/health
```

## 5) Deploy tren Ubuntu production

Gia su repo nam tai `/opt/apps/nhanvu-nnh-safecare-api`.

### 5.1 Re-apply infra (neu moi them `GNH_DB_PASS`)

```bash
cd /opt/apps/nhanvu-nnh-safecare-api/opt/apps/server-a/deploy
./deploy_infra.sh
```

### 5.2 Deploy image service

```bash
cd /opt/apps/nhanvu-nnh-safecare-api/opt/apps/server-a/deploy
./deploy_service.sh image
```

### 5.3 Deploy gnh service

```bash
cd /opt/apps/nhanvu-nnh-safecare-api/opt/apps/server-a/deploy
./deploy_service.sh sheet-sync
./deploy_service.sh gnh
```

### 5.4 Verify

```bash
docker ps | grep svc_gnh
docker logs --tail 200 svc_gnh
curl -fsS http://localhost:8000/health
curl -fsS https://api.safecare.vn/gnh/health
```

## 6) Cau hinh Nginx Proxy Manager (NPM)

Trong Proxy Host `api.safecare.vn`:

- Them custom location:
  - Location: `/gnh`
  - Forward Hostname/IP: `svc_gnh`
  - Forward Port: `8000`

Khuyen nghi:
- Khong rewrite strip prefix cho `/gnh`, vi service da dung `BASE_PATH=/gnh`.
- Sau khi luu, test:
  - `https://api.safecare.vn/gnh/health`

## 7) Mongo auth fail cho `gnh_user` (fix nhanh)

Neu log `svc_gnh` bao `Authentication failed`, tao/update user thu cong.

### Ubuntu

```bash
docker exec -it shared_mongo mongosh -u root_admin -p change-this-password --authenticationDatabase admin --eval "dbx = db.getSiblingDB('db_gnh'); u = dbx.getUser('gnh_user'); if (u) { dbx.updateUser('gnh_user', {pwd:'gnh-strong-pass', roles:[{role:'readWrite', db:'db_gnh'}]}); print('updated gnh_user'); } else { dbx.createUser({user:'gnh_user', pwd:'gnh-strong-pass', roles:[{role:'readWrite', db:'db_gnh'}]}); print('created gnh_user'); }"
```

### Windows PowerShell

```powershell
docker exec -it shared_mongo mongosh -u root_admin -p change-this-password --authenticationDatabase admin --eval "dbx = db.getSiblingDB('db_gnh'); u = dbx.getUser('gnh_user'); if (u) { dbx.updateUser('gnh_user', {pwd:'gnh-strong-pass', roles:[{role:'readWrite', db:'db_gnh'}]}); print('updated gnh_user'); } else { dbx.createUser({user:'gnh_user', pwd:'gnh-strong-pass', roles:[{role:'readWrite', db:'db_gnh'}]}); print('created gnh_user'); }"
```

Verify dang nhap app user:

```bash
docker exec -it shared_mongo mongosh "mongodb://gnh_user:gnh-strong-pass@localhost:27017/db_gnh?authSource=db_gnh" --eval "db.runCommand({ping:1})"
```

### Tao/cap nhat cung luc `gnh_user` va `sheet_sync_user`

Neu ban muon tao/cap nhat nhanh ca 2 user trong 1 lenh:

#### Ubuntu

```bash
docker exec -it shared_mongo mongosh -u root_admin -p change-this-password --authenticationDatabase admin --eval "
dbGnh = db.getSiblingDB('db_gnh');
uGnh = dbGnh.getUser('gnh_user');
if (uGnh) {
  dbGnh.updateUser('gnh_user', {pwd:'gnh-strong-pass', roles:[{role:'readWrite', db:'db_gnh'}]});
  print('updated gnh_user');
} else {
  dbGnh.createUser({user:'gnh_user', pwd:'gnh-strong-pass', roles:[{role:'readWrite', db:'db_gnh'}]});
  print('created gnh_user');
}

dbSheet = db.getSiblingDB('db_sheet_sync');
uSheet = dbSheet.getUser('sheet_sync_user');
if (uSheet) {
  dbSheet.updateUser('sheet_sync_user', {pwd:'sheet-sync-strong-pass', roles:[{role:'readWrite', db:'db_sheet_sync'}]});
  print('updated sheet_sync_user');
} else {
  dbSheet.createUser({user:'sheet_sync_user', pwd:'sheet-sync-strong-pass', roles:[{role:'readWrite', db:'db_sheet_sync'}]});
  print('created sheet_sync_user');
}
"
```

#### Windows PowerShell

```powershell
docker exec -it shared_mongo mongosh -u root_admin -p change-this-password --authenticationDatabase admin --eval "dbGnh = db.getSiblingDB('db_gnh'); uGnh = dbGnh.getUser('gnh_user'); if (uGnh) { dbGnh.updateUser('gnh_user', {pwd:'gnh-strong-pass', roles:[{role:'readWrite', db:'db_gnh'}]}); print('updated gnh_user'); } else { dbGnh.createUser({user:'gnh_user', pwd:'gnh-strong-pass', roles:[{role:'readWrite', db:'db_gnh'}]}); print('created gnh_user'); } dbSheet = db.getSiblingDB('db_sheet_sync'); uSheet = dbSheet.getUser('sheet_sync_user'); if (uSheet) { dbSheet.updateUser('sheet_sync_user', {pwd:'sheet-sync-strong-pass', roles:[{role:'readWrite', db:'db_sheet_sync'}]}); print('updated sheet_sync_user'); } else { dbSheet.createUser({user:'sheet_sync_user', pwd:'sheet-sync-strong-pass', roles:[{role:'readWrite', db:'db_sheet_sync'}]}); print('created sheet_sync_user'); }"
```

Sau do redeploy:

```bash
cd /opt/apps/nhanvu-nnh-safecare-api/opt/apps/server-a/deploy
./deploy_service.sh gnh
```

## 8) Van hanh sync Google Sheet

### 8.1 Sync thu cong qua API

```bash
curl -X POST https://api.safecare.vn/gnh/sync \
  -H "Content-Type: application/json" \
  -d '{"api_token":"<GNH_WRITE_TOKEN>"}'
```

### 8.2 Chay loop sync (tuy chon)

Service API hien tai khong auto start loop command. Neu can loop lien tuc, chay command trong container:

```bash
docker exec -d svc_gnh sh -lc "python manage.py run_gnh_sync_loop --interval 30"
```

Luu y:
- Chi nen chay 1 loop process duy nhat.
- Khi container restart, can chay lai lenh tren neu van muon loop.

## 9) Smoke test API

```bash
curl -X POST https://api.safecare.vn/gnh/gets \
  -H "Content-Type: application/json" \
  -d '{"api_token":"<GNH_READ_TOKEN>","page":1,"page_size":10}'
```

Expected:
- HTTP 200
- JSON co `ok: true`

## 10) Rollback

### Windows

```powershell
Set-Location .\opt\apps\server-a\services\gnh
docker compose -f docker-compose.prod.yml down
```

### Ubuntu

```bash
cd /opt/apps/nhanvu-nnh-safecare-api/opt/apps/server-a/services/gnh
docker compose -f docker-compose.prod.yml down
```

Neu can rollback ve image cu:
- checkout commit truoc do
- `./deploy_service.sh gnh` (Ubuntu) hoac `.\deploy_service.ps1 gnh` (Windows)
