# Deploy Image Service (`/image`) on Windows and Ubuntu

This guide deploys the new `image` service (`svc_image`) for:
- `GET /image/get_image` (GNH image)
- `GET /image/good_image` (good image)
- Drive upload/delete and S3 upload/delete APIs

## 1) Prerequisites

- Docker Engine + Docker Compose v2
- Existing Server A stack structure in this repo
- External networks available:
  - `proxy-network`
  - `infra-network`
- Nginx Proxy Manager (NPM) already running in your environment

## 2) Files involved

- Service code: `opt/apps/server-a/code/image-backend`
- Service compose: `opt/apps/server-a/services/image/docker-compose.prod.yml`
- Service env: `opt/apps/server-a/services/image/.env`
- Secret mount (Drive service account):
  - Host path: `opt/apps/server-a/services/image/secrets/safedatabase-a88bf902aa78.json`
  - Container path: `/run/secrets/safedatabase-a88bf902aa78.json`

## 3) Configure environment and secret

1. Review and update env:
   - `opt/apps/server-a/services/image/.env`

2. Place Google service-account JSON:
   - Create file at:
     - `opt/apps/server-a/services/image/secrets/safedatabase-a88bf902aa78.json`

3. Ensure `.env` matches this mounted secret path:
   - `GOOGLE_SERVICE_ACCOUNT_FILE=/run/secrets/safedatabase-a88bf902aa78.json`

4. If Mongo user `image_user` does not exist yet, ensure infra env contains:
   - `IMAGE_DB_PASS=...` in `opt/apps/server-a/infra/.env.infra`

## 4) Deploy on Windows

From repo root (`E:\CodeAd2026\nhanvu-nnh-safecare-api`):

```powershell
Set-Location .\opt\apps\server-a\deploy

# (Optional) re-apply infra if you just added IMAGE_DB_PASS or changed mongo init
.\deploy_infra.ps1

# Deploy image service
.\deploy_service.ps1 image
```

If your environment does not have `deploy_infra.ps1`, run infra compose manually:

```powershell
Set-Location ..\infra
docker compose -f docker-compose.infra.yml up -d
```

## 5) Deploy on Ubuntu

From repo root (example: `/opt/apps/server-a` layout):

```bash
cd /opt/apps/server-a/deploy

# (Optional) re-apply infra if you just added IMAGE_DB_PASS or changed mongo init
./deploy_infra.sh

# Deploy image service
./deploy_service.sh image
```

## 6) Configure Nginx Proxy Manager

In Proxy Host for your API domain (for example `api.safecare.vn`):

- Add custom location:
  - Location: `/image`
  - Forward Hostname / IP: `svc_image`
  - Forward Port: `8000`

If needed, add rewrite (Advanced) to strip prefix:

```nginx
rewrite ^/image/(.*)$ /$1 break;
```

## 7) Verify deployment

### Internal container checks

```bash
docker ps | grep svc_image
docker logs -f svc_image
```

### Health checks

- Direct (inside docker network path via NPM route):

```bash
curl https://api.safecare.vn/image/health
```

Expected response:

```json
{"status":"ok"}
```

### Endpoint compatibility checks

```bash
curl "https://api.safecare.vn/image/get_image?file=test.jpg"
curl "https://api.safecare.vn/image/good_image?file=drive:example.jpg"
```

## 8) Common issues

1. `File not found` for service account JSON
- Ensure host file exists:
  - `opt/apps/server-a/services/image/secrets/safedatabase-a88bf902aa78.json`
- Ensure compose mount path exactly matches `.env`.

2. Mongo auth error for `image_user`
- Confirm `IMAGE_DB_PASS` in `opt/apps/server-a/infra/.env.infra`
- Re-apply infra init and verify user in `db_image`.

### Fix `pymongo.errors.OperationFailure: Authentication failed` (code 18)

If `svc_image` logs show Mongo auth failed, create/update `image_user` directly.

1. Ensure password is consistent:
- `opt/apps/server-a/infra/.env.infra` -> `IMAGE_DB_PASS=...`
- `opt/apps/server-a/services/image/.env` -> `MONGO_URI` uses same password

2. Create/update Mongo user manually

Ubuntu:

```bash
docker exec -it shared_mongo mongosh -u root_admin -p change-this-password --authenticationDatabase admin --eval "
dbx = db.getSiblingDB('db_image');
u = dbx.getUser('image_user');
if (u) {
  dbx.updateUser('image_user', {pwd:'image-strong-pass', roles:[{role:'readWrite', db:'db_image'}]});
  print('updated image_user');
} else {
  dbx.createUser({user:'image_user', pwd:'image-strong-pass', roles:[{role:'readWrite', db:'db_image'}]});
  print('created image_user');
}
"
```

Windows PowerShell:

```powershell
docker exec -it shared_mongo mongosh -u root_admin -p change-this-password --authenticationDatabase admin --eval "dbx = db.getSiblingDB('db_image'); u = dbx.getUser('image_user'); if (u) { dbx.updateUser('image_user', {pwd:'image-strong-pass', roles:[{role:'readWrite', db:'db_image'}]}); print('updated image_user'); } else { dbx.createUser({user:'image_user', pwd:'image-strong-pass', roles:[{role:'readWrite', db:'db_image'}]}); print('created image_user'); }"
```

3. Verify login with app user:

```bash
docker exec -it shared_mongo mongosh "mongodb://image_user:image-strong-pass@localhost:27017/db_image?authSource=db_image" --eval "db.runCommand({ping:1})"
```

4. Redeploy image service:

Ubuntu:

```bash
cd /opt/apps/server-a/deploy
./deploy_service.sh image
```

Windows:

```powershell
Set-Location .\opt\apps\server-a\deploy
.\deploy_service.ps1 image
```

3. `404` on `/image/*`
- Verify NPM custom location `/image -> svc_image:8000`
- Add rewrite if prefix is not stripped.

4. S3 access errors
- Re-check `.env` values:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_STORAGE_BUCKET_NAME`
  - `AWS_BUCKET`

## 9) Rollback

Windows:

```powershell
Set-Location .\opt\apps\server-a\services\image
docker compose -f docker-compose.prod.yml down
```

Ubuntu:

```bash
cd /opt/apps/server-a/services/image
docker compose -f docker-compose.prod.yml down
```
