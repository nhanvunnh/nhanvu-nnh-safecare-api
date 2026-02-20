# nhanvu-nnh-safecare-api

Hệ thống Server A phục vụ domain `api.safecare.vn` với MongoDB dùng chung, Redis nền tảng, các service Django/Gunicorn (auth, sms, shop, laydi, core) và Nginx Proxy Manager (NPM) path-based routing.

## API docs

- `docs/api-auth.md`
- `docs/api-sms.md`

## Backend URL cố định

- Dev: `http://192.168.1.5:8090`
- Prod: `https://api.safecare.vn`

## Deploy guides

- `LIGHTSAIL_UBUNTU_DEPLOY_GUIDE.md`

## Directory layout

```
opt/
└── apps/
	└── server-a/
		├── infra/
		│   ├── docker-compose.infra.yml
		│   ├── .env.infra
		│   └── mongo_init/
		│       └── create_app_users.js
		├── services/
		│   ├── auth/
		│   ├── sms/
		│   ├── shop/
		│   ├── laydi/
		│   └── core/
		└── deploy/
			├── deploy_infra.sh
			├── deploy_service.sh
			└── backup_mongo.sh
```

Mỗi service folder chứa cặp `docker-compose.prod.yml` + `.env` riêng.

## Prerequisites

- Docker Engine ≥ 24, Docker Compose v2.
- Domain `api.safecare.vn` trỏ A record về Server A.
- Cổng mở: 80/443 cho public, 81 (NPM UI) chỉ whitelist IP quản trị, SSH whitelist IP.
- Hostname/OS timezone cấu hình đúng (`Asia/Ho_Chi_Minh`).

## Bootstrap Docker networks

Hệ sinh thái yêu cầu 2 external network: `proxy-network` (NPM ↔ services) và `infra-network` (services ↔ Mongo/Redis).

```bash
docker network create proxy-network
docker network create infra-network
```

Các compose file tham chiếu network external này, vì vậy phải tồn tại trước khi deploy.

## Infrastructure stack

- NPM, MongoDB, Redis được định nghĩa tại [opt/apps/server-a/infra/docker-compose.infra.yml](opt/apps/server-a/infra/docker-compose.infra.yml).
- Biến môi trường/secret khai báo trong [opt/apps/server-a/infra/.env.infra](opt/apps/server-a/infra/.env.infra) (không commit bản production).
- MongoDB auth bật bằng `MONGO_INITDB_ROOT_*` và script init [opt/apps/server-a/infra/mongo_init/create_app_users.js](opt/apps/server-a/infra/mongo_init/create_app_users.js) tạo database/user cho từng service. Script tự cập nhật password nếu user tồn tại.
- MongoDB/Redis không publish port ra host. Các volume data nằm trong `infra/data/*` (Docker tự tạo).

Triển khai hoặc cập nhật stack bằng script [opt/apps/server-a/deploy/deploy_infra.sh](opt/apps/server-a/deploy/deploy_infra.sh):

```bash
cd opt/apps/server-a/deploy
chmod +x deploy_infra.sh
./deploy_infra.sh
```

Script sẽ đảm bảo network tồn tại, load `.env.infra`, `docker compose pull`, sau đó `up -d`.

## Service stacks (auth, sms, shop, laydi, core)

Mỗi service có một compose file riêng trong thư mục tương ứng, ví dụ [opt/apps/server-a/services/auth/docker-compose.prod.yml](opt/apps/server-a/services/auth/docker-compose.prod.yml).

### Code workspace (opt/apps/server-a/code)

- Tất cả mã nguồn ứng dụng được gom trong thư mục [opt/apps/server-a/code](opt/apps/server-a/code). Mỗi module có một thư mục riêng dạng `<module>-backend` để dễ quản lý và nhân bản về sau.
- Service Auth nằm tại [opt/apps/server-a/code/auth-backend](opt/apps/server-a/code/auth-backend) (JWT + MongoEngine + OAuth). Tài liệu cụ thể nằm trong [opt/apps/server-a/code/auth-backend/README.md](opt/apps/server-a/code/auth-backend/README.md).
- Hiện tại service SMS nằm tại [opt/apps/server-a/code/sms-backend](opt/apps/server-a/code/sms-backend) cùng với tài liệu chi tiết trong [opt/apps/server-a/code/sms-backend/README.md](opt/apps/server-a/code/sms-backend/README.md).
- Khi thêm module mới (ví dụ auth), chỉ cần tạo thêm thư mục `opt/apps/server-a/code/auth-backend/` chứa code và Dockerfile. Compose sản phẩm tương ứng sẽ nằm ở `opt/apps/server-a/services/auth/`.
- Với SMS, compose production ở `opt/apps/server-a/services/sms/docker-compose.prod.yml` đã tham chiếu trực tiếp build context `../../code/sms-backend`, nên không cần copy code qua lại giữa các thư mục.

### Environment contract

.env mẫu cho từng service (ví dụ [opt/apps/server-a/services/auth/.env](opt/apps/server-a/services/auth/.env)) đã bao gồm các biến chuẩn:

- `APP_NAME`, `APP_ENV=production`.
- `BASE_PATH`/`FORCE_SCRIPT_NAME` = `/auth`, `/sms`, `/shop`, `/laydi`, `/core` tương ứng.
- `MONGO_URI` dạng `mongodb://<user>:<pass>@shared_mongo:27017/<db>?authSource=<db>` (vì user được tạo trong chính DB app như `db_auth`, `db_sms`).
- `REDIS_URL` tùy chọn `redis://:password@shared_redis:6379/<db-index>`.
- `ALLOWED_HOSTS` = `api.safecare.vn`, `CSRF_TRUSTED_ORIGINS = https://api.safecare.vn`.
- `SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST`, `TRUST_X_FORWARDED_PROTO` bật để nhận header từ NPM.
- `SECRET_KEY`, `DJANGO_SETTINGS_MODULE`, `LOG_LEVEL` placeholder.

Command Gunicorn mặc định: `gunicorn app.wsgi:application --bind 0.0.0.0:8000 --workers 2`. Có thể chỉnh trong compose nếu cần.

### Deploy một service

```bash
cd opt/apps/server-a/deploy
chmod +x deploy_service.sh
./deploy_service.sh auth   # hoặc sms|shop|laydi|core
```

Script tạo network nếu thiếu, đảm bảo `.env` tồn tại, rồi `docker compose pull` + `up -d --remove-orphans` cho service tương ứng.

### Healthcheck contract

Mỗi service phải có endpoint `GET {BASE_PATH}/health` (qua NPM) hoặc `GET /health` nội bộ trả `200 {"status":"ok"}` không cần auth. Compose healthcheck đã gọi `http://localhost:8000/health` để Docker quản lý trạng thái.

## Nginx Proxy Manager routing

Tạo một Proxy Host `api.safecare.vn` trong NPM:

1. Forward host/port mặc định có thể trỏ tạm `svc_core:8000`.
2. Request Let’s Encrypt, bật Force SSL + HTTP/2.
3. Bật các header pass-through: `Host`, `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Real-IP`.
4. Trong tab Custom Locations, thêm:
   - `/auth` → `svc_auth:8000`
   - `/sms` → `svc_sms:8000`
   - `/shop` → `svc_shop:8000`
   - `/laydi` → `svc_laydi:8000`
   - `/core` → `svc_core:8000`
5. Nếu framework không hỗ trợ prefix, bật rewrite `/prefix/(.*) → /$1` (NPM UI > Advanced > `rewrite ^/auth/(.*)$ /$1 break;`).

Port 81 (UI) nên hạn chế bằng firewall/SG.

## Mongo backup script

- Script [opt/apps/server-a/deploy/backup_mongo.sh](opt/apps/server-a/deploy/backup_mongo.sh) dùng `docker exec shared_mongo mongodump --archive --gzip` và lưu file `mongo-<timestamp>.archive.gz` tại `/opt/backups/mongo` (có thể override `BACKUP_ROOT`).
- Đặt `RETENTION_COUNT` (mặc định 7) để giữ số bản backup gần nhất. Tích hợp cron ví dụ: `0 2 * * * BACKUP_ROOT=/opt/backups/mongo /opt/apps/server-a/deploy/backup_mongo.sh`.

## Security & operations checklist

- `.env` files chứa secret, không commit bản production.
- Chỉ publish port 80/443/81. Mongo/Redis nằm trong `infra-network` riêng.
- Đặt password mạnh trong `.env.infra` và `.env` service, thay ngay các placeholder.
- Theo dõi Docker logs (`docker logs -f svc_auth`) và tài nguyên (`docker stats`).
- Thiết lập giám sát backup để bảo đảm file được tạo định kỳ.

## Troubleshooting

- `curl https://api.safecare.vn/auth/health` phải trả JSON `{"status":"ok"}` khi routing chuẩn.
- `curl https://api.safecare.vn/sms/health` xác nhận service SMS hoạt động qua NPM rewrite `/sms`.
- Nếu service không thấy Mongo, kiểm tra network attach (`docker network inspect infra-network`).
- Kiểm tra logs NPM tại container `npm` nếu SSL hoặc rewrite không hoạt động.
