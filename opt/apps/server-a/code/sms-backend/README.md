# SafeCare SMS Service

Django 4 / DRF + PyMongo service that powers SMS templates, API-key driven queues, Android agent leasing, and reporting. The service is designed to live under `/sms` on `api.safecare.vn` via the Server A stack.

## Repo layout

```
sms-backend/
â”œâ”€â”€ config/                 # Django project (settings, urls, wsgi)
â”œâ”€â”€ sms_gateway/            # Business logic + REST APIs
â”‚   â”œâ”€â”€ admin_api.py        # Admin API-key management (JWT)
â”‚   â”œâ”€â”€ agent_api.py        # Android agent register/heartbeat/leasing/report
â”‚   â”œâ”€â”€ templates_api.py    # Template CRUD/approve (JWT)
â”‚   â”œâ”€â”€ requests_api.py     # Send requests + status (API key/JWT)
â”‚   â”œâ”€â”€ reports_api.py      # Summary + CSV export (JWT)
â”‚   â”œâ”€â”€ auth.py             # DRF auth classes (API key / Agent / JWT)
â”‚   â”œâ”€â”€ mongo.py            # PyMongo client helpers
â”‚   â”œâ”€â”€ utils.py            # Rendering, audit helpers, phone utils
â”‚   â”œâ”€â”€ indexes.py          # Mongo index definitions
â”‚   â””â”€â”€ management/commands # create_indexes, seed_admin
â”œâ”€â”€ manage.py
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ Dockerfile
â”œâ”€â”€ docker-compose.yml          # Local dev (backend + mongo)
â”œâ”€â”€ docker-compose.prod.yml     # Production compose (Server A service folder)
â””â”€â”€ .env.example
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

## API quick reference

- `GET /sms/health` - health check
- `GET /sms/admin/agent/registration-secret` - get current `registration_secret` (JWT required)
- `PUT /sms/admin/agent/registration-secret` - create/update `registration_secret` in DB (JWT required)
- `POST /sms/admin/api-keys` - create API key (JWT required)
- `POST /sms/agent/register` - register/rotate agent token (optional `registration_secret`, existing `device_id` rotates by default; send `rotate_token=false` to skip)
- `POST /sms/templates` - create template (JWT required)
- `POST /sms/requests` - create SMS request (`X-API-Key` required, must include `agent_id`)
- `GET /sms/messages/all` - list all messages (JWT sees all, API key sees own messages)

### Sample flows

Assume you already obtained a JWT (`$JWT`) from auth-service and you are running locally (`http://localhost:8000`).

1. **Create API key (JWT)**
   ```bash
   curl -X POST http://localhost:8000/sms/admin/api-keys \
     -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d '{"client_name":"SafeShop","scopes":["sms:send","sms:read"],"rate_limit_per_day":5000}'
   ```
   Response includes `plain_key` once. Save it as `$API_KEY`.

2. **Get agent registration secret (JWT)**
   ```bash
   curl -X GET http://localhost:8000/sms/admin/agent/registration-secret \
     -H "Authorization: Bearer $JWT"
   ```
   Response:
   ```json
   {
     "registration_secret": "your-shared-secret",
     "configured": true
   }
   ```

3. **Create/update agent registration secret in DB (JWT)**
   ```bash
   curl -X PUT http://localhost:8000/sms/admin/agent/registration-secret \
     -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d '{"registration_secret":"your-new-secret-2026"}'
   ```
   Send empty value to disable:
   ```bash
   curl -X PUT http://localhost:8000/sms/admin/agent/registration-secret \
     -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d '{"registration_secret":""}'
   ```

4. **Agent register (get AGENT_ID + AGENT_TOKEN)**
   ```bash
   AGENT_REGISTER_JSON=$(curl -s -X POST http://localhost:8000/sms/agent/register \
     -H "Content-Type: application/json" \
     -d '{"device_id":"agent-001","label":"Android-01","registration_secret":"'$AGENT_SECRET'"}')
   AGENT_ID=$(echo "$AGENT_REGISTER_JSON" | jq -r '.agent_id')
   AGENT_TOKEN=$(echo "$AGENT_REGISTER_JSON" | jq -r '.agent_token')
   ```

5. **Create + approve template (JWT)**
   ```bash
   TEMPLATE_ID=$(curl -s -X POST http://localhost:8000/sms/templates \
     -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d '{"name":"otp","content":"Ma OTP {CODE}"}' | jq -r '.id')

   curl -X POST http://localhost:8000/sms/templates/$TEMPLATE_ID/approve \
     -H "Authorization: Bearer $JWT"
   ```

6. **Send SMS request (API key)**
   ```bash
   curl -X POST http://localhost:8000/sms/requests \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
          "template_id":"'$TEMPLATE_ID'",
          "agent_id":"'$AGENT_ID'",
          "messages":[{"to":"0901234567","variables":{"CODE":"123456"}}]
        }'
   ```

7. **Get request detail + list by request**
   ```bash
   REQUEST_ID=$(curl -s -X POST http://localhost:8000/sms/requests \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
          "template_id":"'$TEMPLATE_ID'",
          "agent_id":"'$AGENT_ID'",
          "messages":[{"to":"0901234567","variables":{"CODE":"999999"}}]
        }' | jq -r '.request_id')

   curl -X GET http://localhost:8000/sms/requests/$REQUEST_ID \
     -H "X-API-Key: $API_KEY"

   curl -X GET "http://localhost:8000/sms/messages?request_id=$REQUEST_ID&limit=50&skip=0" \
     -H "X-API-Key: $API_KEY"
   ```

8. **List all messages (new endpoint)**
   ```bash
   # API key: only messages belonging to this key
   curl -X GET "http://localhost:8000/sms/messages/all?limit=50&skip=0&status=PENDING" \
     -H "X-API-Key: $API_KEY"

   # JWT: all messages in the system
   curl -X GET "http://localhost:8000/sms/messages/all?agent_id=$AGENT_ID&limit=50&skip=0" \
     -H "Authorization: Bearer $JWT"
   ```

9. **Agent lease / report**
   ```bash
   curl -X GET "http://localhost:8000/sms/agent/jobs/next?limit=10" \
     -H "Authorization: Bearer $AGENT_TOKEN"

   curl -X POST http://localhost:8000/sms/agent/messages/report \
     -H "Authorization: Bearer $AGENT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"messages":[{"message_id":"...","status":"SENT"}]}'
   ```

## Deploy on Server A

1. Äáº·t mÃ£ nguá»“n táº¡i `opt/apps/server-a/code/sms-backend` (náº¿u develop á»Ÿ nÆ¡i khÃ¡c, sync ná»™i dung repo vá» thÆ° má»¥c nÃ y trÆ°á»›c khi deploy).
2. Tá»« thÆ° má»¥c `opt/apps/server-a/services/sms` táº¡o `.env` theo máº«u, trá» `MONGO_URI` vá» `shared_mongo` user `sms_user`.
3. Äáº£m báº£o external networks (`proxy-network`, `infra-network`) Ä‘Ã£ Ä‘Æ°á»£c táº¡o theo README tá»•ng.
4. Tá»« thÆ° má»¥c deploy chung trÃªn Server A cháº¡y:
   ```bash
   cd /opt/apps/server-a/deploy
   ./deploy_service.sh sms
   ```
   Windows PowerShell:
   ```powershell
   Set-Location E:\CodeAd2026\nhanvu-nnh-safecare-api\opt\apps\server-a\deploy
   .\deploy_service.ps1 sms
   ```
   The script executes `docker compose -f services/sms/docker-compose.prod.yml up -d --remove-orphans`, which in turn builds the included Dockerfile, runs `manage.py create_indexes`, `seed_admin`, then starts Gunicorn on port 8000 inside the container.
5. Configure Nginx Proxy Manager:
   - Proxy Host: `api.safecare.vn`
   - Custom location `/sms` â†’ `svc_sms:8000`, enable prefix rewrite (`/sms/(.*) -> /$1`) so Django sees routes without `/sms`.
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

- Internal (container): `GET /health` â†’ Docker healthcheck hits `http://localhost:8000/health`.
- External (NPM): `GET https://api.safecare.vn/sms/health` â†’ proxies through `/sms` location.

## Message statuses

- `PENDING`: tin nhắn vừa được tạo, đang chờ agent nhận job.
- `ASSIGNED`: tin nhắn đã được gán cho một agent, đang chờ xử lý trên thiết bị.
- `SENDING`: thiết bị đang thực hiện gửi tin nhắn.
- `SENT`: thiết bị đã báo gửi thành công lên carrier/SMS stack.
- `DELIVERED`: đã có xác nhận phát đến đích (sau trạng thái `SENT`).
- `FAILED`: gửi thất bại trên thiết bị (có thể kèm `last_error`).
- `CANCELED`: bị hủy trước khi gửi (ví dụ trùng nội dung trong cửa sổ chống trùng).

Luồng chuyển trạng thái hợp lệ:

- `PENDING -> ASSIGNED|SENDING|SENT|FAILED`
- `ASSIGNED -> SENDING|SENT|FAILED`
- `SENDING -> SENT|FAILED`
- `SENT -> DELIVERED`
## Notes

- API keys enforce scopes (`sms:send`, `sms:read`) and per-day rate limits via Mongo aggregations.
- Duplicate suppression: if the same `to + text` occurs within `ANTI_DUP_MINUTES`, a `CANCELED` message is recorded with `last_error="DUPLICATE_RECENT"`.
- Agents lease jobs atomically with `find_one_and_update`, prioritized by `priority_weight` and `created_at`, and report results with strict state transitions (no regression from `DELIVERED`).
- CSV export streams via `StreamingHttpResponse` to avoid loading all rows into memory.

