# Deploy Sheet Sync Service (`/sheet`) on Windows and Ubuntu

Service `sheet-sync` la API dong bo Google Sheet dung chung cho nhieu module (GNH va cac app khac sau nay).

## 1) Files lien quan

- Code: `opt/apps/server-a/code/sheet-sync-backend`
- Service compose: `opt/apps/server-a/services/sheet-sync/docker-compose.prod.yml`
- Service env: `opt/apps/server-a/services/sheet-sync/.env`
- Secret file:
  - Host: `opt/apps/server-a/services/sheet-sync/secrets/safedatabase-a88bf902aa78.json`
  - Container: `/run/secrets/safedatabase-a88bf902aa78.json`
- Infra env: `opt/apps/server-a/infra/.env.infra`
- Mongo init: `opt/apps/server-a/infra/mongo_init/create_app_users.js`

## 2) Env can kiem tra

### 2.1 Infra

`opt/apps/server-a/infra/.env.infra`

```env
SHEET_SYNC_DB_PASS=sheet-sync-strong-pass
```

### 2.2 Sheet-sync service

`opt/apps/server-a/services/sheet-sync/.env`

```env
BASE_PATH=/sheet
MONGO_URI=mongodb://sheet_sync_user:sheet-sync-strong-pass@shared_mongo:27017/db_sheet_sync?authSource=db_sheet_sync
MONGO_DB=db_sheet_sync
SYNC_MONGO_URI=mongodb://root_admin:<root-pass>@shared_mongo:27017/admin?authSource=admin
INTERNAL_SERVICE_TOKEN=change-me-internal-token
GOOGLE_SERVICE_ACCOUNT_FILE=/run/secrets/safedatabase-a88bf902aa78.json
```

`SYNC_MONGO_URI` can quyen doc/ghi DB dich (vd `db_gnh`) de dong bo du lieu.

## 3) Deploy tren Windows

```powershell
Set-Location .\opt\apps\server-a\deploy

# neu moi them SHEET_SYNC_DB_PASS
.\deploy_infra.ps1

# deploy service
.\deploy_service.ps1 sheet-sync
```

## 4) Deploy tren Ubuntu

```bash
cd /opt/apps/nhanvu-nnh-safecare-api/opt/apps/server-a/deploy

# neu moi them SHEET_SYNC_DB_PASS
./deploy_infra.sh

# deploy service
./deploy_service.sh sheet-sync
```

## 5) Cau hinh NPM

Trong Proxy Host `api.safecare.vn`:
- Location: `/sheet`
- Forward host: `svc_sheet_sync`
- Forward port: `8000`

Khong rewrite strip prefix.

## 6) Verify

```bash
curl -fsS https://api.safecare.vn/sheet/health
```

Expected:

```json
{"status":"ok"}
```

## 6.1) Mongo auth fail (fix nhanh)

Neu `svc_sheet_sync` bao loi `Authentication failed`, tao/cap nhat user nhu sau.

### Ubuntu

```bash
docker exec -it shared_mongo mongosh -u root_admin -p change-this-password --authenticationDatabase admin --eval "
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

### Windows PowerShell

```powershell
docker exec -it shared_mongo mongosh -u root_admin -p change-this-password --authenticationDatabase admin --eval "dbSheet = db.getSiblingDB('db_sheet_sync'); uSheet = dbSheet.getUser('sheet_sync_user'); if (uSheet) { dbSheet.updateUser('sheet_sync_user', {pwd:'sheet-sync-strong-pass', roles:[{role:'readWrite', db:'db_sheet_sync'}]}); print('updated sheet_sync_user'); } else { dbSheet.createUser({user:'sheet_sync_user', pwd:'sheet-sync-strong-pass', roles:[{role:'readWrite', db:'db_sheet_sync'}]}); print('created sheet_sync_user'); }"
```

Kiem tra login:

```bash
docker exec -it shared_mongo mongosh "mongodb://sheet_sync_user:sheet-sync-strong-pass@localhost:27017/db_sheet_sync?authSource=db_sheet_sync" --eval "db.runCommand({ping:1})"
```

## 7) APIs chinh

- `POST /sheet/apps/upsert`
- `POST /sheet/apps/get`
- `POST /sheet/apps/list`
- `POST /sheet/jobs/run`
- `POST /sheet/logs/list`

## 8) Rollback

### Windows

```powershell
Set-Location .\opt\apps\server-a\services\sheet-sync
docker compose -f docker-compose.prod.yml down
```

### Ubuntu

```bash
cd /opt/apps/nhanvu-nnh-safecare-api/opt/apps/server-a/services/sheet-sync
docker compose -f docker-compose.prod.yml down
```

## 9) Tham khao mapping URL khi tach server

- Xem: `docs/SERVICE_URL_MAPPING_SPLIT_SERVERS.md`
- Muc tieu: doi URL lien service (`auth`, `image`, `sheet-sync`, `gnh`) chi bang env.
