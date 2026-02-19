# SafeCare SMS Service

Django 4 / DRF + PyMongo service that powers SMS templates, API-key driven queues, Android agent leasing, and reporting. The service is designed to live under `/sms` on `api.safecare.vn` via the Server A stack.

## Repo layout

```
sms-backend/
├── config/                 # Django project (settings, urls, wsgi)
├── sms_gateway/            # Business logic + REST APIs
│   ├── admin_api.py        # Admin API-key management (JWT)
│   ├── agent_api.py        # Android agent register/heartbeat/leasing/report
│   ├── templates_api.py    # Template CRUD/approve (JWT)
│   ├── requests_api.py     # Send requests + status (API key/JWT)
│   ├── reports_api.py      # Summary + CSV export (JWT)
│   ├── auth.py             # DRF auth classes (API key / Agent / JWT)
│   ├── mongo.py            # PyMongo client helpers
│   ├── utils.py            # Rendering, audit helpers, phone utils
│   ├── indexes.py          # Mongo index definitions
│   └── management/commands # create_indexes, seed_admin
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml          # Local dev (backend + mongo)
├── docker-compose.prod.yml     # Production compose (Server A service folder)
└── .env.example
```

## Environment contract

Copy `.env.example` to `.env` (for prod) and align values with Server A README:

```
APP_NAME=sms
APP_ENV=production
BASE_PATH=/sms
DJANGO_SECRET_KEY=***
DJANGO_DEBUG=0
ALLOWED_HOSTS=api.safecare.vn
CSRF_TRUSTED_ORIGINS=https://api.safecare.vn
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
USE_X_FORWARDED_HOST=true
MONGO_URI=mongodb://sms_user:***@shared_mongo:27017/db_sms?authSource=db_sms
MONGO_DB=db_sms
JWT_SECRET=***
JWT_ACCESS_MINUTES=240
LEASE_SECONDS=300
AGENT_RATE_LIMIT_PER_MIN=10
APIKEY_RATE_LIMIT_PER_DAY_DEFAULT=20000
DEFAULT_COUNTRY_PREFIX=+84
BLOCK_INTERNATIONAL=1
ANTI_DUP_MINUTES=3
MAX_RECIPIENTS_PER_REQUEST=5000
MAX_TEXT_LENGTH=1600
SEED_ADMIN=1
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=admin123
AGENT_REGISTRATION_SECRET=<optional shared secret for new agents>
```

## Run locally

1. Copy `.env.example` to `.env` (optional for prod secrets). For local dev the compose file reads `.env.example`.
2. Start services:
   ```bash
   docker compose up --build
   ```
3. Open a new terminal:
   ```bash
   docker compose exec backend python manage.py create_indexes
   docker compose exec backend python manage.py seed_admin
   ```
4. Hit healthcheck:
   ```bash
   curl http://localhost:8000/health
   ```

### Sample flows

Assume you already obtained a JWT (`$JWT`) from auth-service and you are running locally (`http://localhost:8000`).

1. **Create API key (JWT)**
   ```bash
   curl -X POST http://localhost:8000/admin/api-keys \
     -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d '{"client_name":"SafeShop","scopes":["sms:send","sms:read"],"rate_limit_per_day":5000}'
   ```
   Response includes `plain_key` once. Save it as `$API_KEY`.

2. **Create + approve template (JWT)**
   ```bash
   TEMPLATE_ID=$(curl -s -X POST http://localhost:8000/templates \
     -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d '{"name":"otp","content":"Ma OTP {CODE}"}' | jq -r '.id')

   curl -X POST http://localhost:8000/templates/$TEMPLATE_ID/approve \
     -H "Authorization: Bearer $JWT"
   ```

3. **Send SMS request (API key)**
   ```bash
   curl -X POST http://localhost:8000/requests \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
          "template_id":"'$TEMPLATE_ID'",
          "messages":[{"to":"0901234567","variables":{"CODE":"123456"}}]
        }'
   ```

4. **Agent register / lease / report**
   ```bash
   AGENT_TOKEN=$(curl -s -X POST http://localhost:8000/agent/register \
     -H "Content-Type: application/json" \
     -d '{"device_id":"agent-001","label":"Android-01","registration_secret":"'$AGENT_SECRET'"}' | jq -r '.agent_token')

   curl -X GET "http://localhost:8000/agent/jobs/next?limit=10" \
     -H "Authorization: Bearer $AGENT_TOKEN"

   curl -X POST http://localhost:8000/agent/messages/report \
     -H "Authorization: Bearer $AGENT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"messages":[{"message_id":"...","status":"SENT"}]}'
   ```

## Deploy on Server A

1. Đặt mã nguồn tại `opt/apps/server-a/code/sms-backend` (nếu develop ở nơi khác, sync nội dung repo về thư mục này trước khi deploy).
2. Từ thư mục `opt/apps/server-a/services/sms` tạo `.env` theo mẫu, trỏ `MONGO_URI` về `shared_mongo` user `sms_user`.
3. Đảm bảo external networks (`proxy-network`, `infra-network`) đã được tạo theo README tổng.
4. Từ thư mục deploy chung trên Server A chạy:
   ```bash
   cd /opt/apps/server-a/deploy
   ./deploy_service.sh sms
   ```
   The script executes `docker compose -f services/sms/docker-compose.prod.yml up -d --remove-orphans`, which in turn builds the included Dockerfile, runs `manage.py create_indexes`, `seed_admin`, then starts Gunicorn on port 8000 inside the container.
5. Configure Nginx Proxy Manager:
   - Proxy Host: `api.safecare.vn`
   - Custom location `/sms` → `svc_sms:8000`, enable prefix rewrite (`/sms/(.*) -> /$1`) so Django sees routes without `/sms`.
6. Verify:
   ```bash
   curl https://api.safecare.vn/sms/health
   ```

## Mongo collections

- `templates`
- `api_keys`
- `agents`
- `sms_requests`
- `sms_messages`
- `audit_logs`

Run `python manage.py create_indexes` to (re)apply all required indexes after deployment.

## Healthchecks

- Internal (container): `GET /health` → Docker healthcheck hits `http://localhost:8000/health`.
- External (NPM): `GET https://api.safecare.vn/sms/health` → proxies through `/sms` location.

## Notes

- API keys enforce scopes (`sms:send`, `sms:read`) and per-day rate limits via Mongo aggregations.
- Duplicate suppression: if the same `to + text` occurs within `ANTI_DUP_MINUTES`, a `CANCELED` message is recorded with `last_error="DUPLICATE_RECENT"`.
- Agents lease jobs atomically with `find_one_and_update`, prioritized by `priority_weight` and `created_at`, and report results with strict state transitions (no regression from `DELIVERED`).
- CSV export streams via `StreamingHttpResponse` to avoid loading all rows into memory.
