# SMS Module API (sms-backend)

Các endpoint dưới đây là đường dẫn **tại root của service**. Khi đi qua Nginx Proxy Manager (path-based routing), thường sẽ map dưới prefix `/sms`, ví dụ: `/sms/health`, `/sms/templates`, ...

## Authentication

SMS backend hỗ trợ 3 kiểu principal:

1) **JWT user** (cho admin/operator):
   - Header: `Authorization: Bearer <jwt>` (token có dấu `.`)
   - Dùng cho: templates, reports, quản lý API key.

2) **API Key principal** (cho client gửi/tra cứu SMS):
   - Header: `X-API-Key: <plain_key>`
   - Scopes:
     - `sms:send` (gửi)
     - `sms:read` (xem request/messages)

3) **Agent principal** (cho thiết bị/agent gửi tin):
   - Header: `Authorization: Bearer <agent_token>` (token **không** có dấu `.`)
   - Dùng cho: agent/*.

## Health

- `GET /health` → `200 {"status":"ok"}`

## Admin: API keys (JWT required)

### List API keys

- `GET /admin/api-keys`
- Response: danh sách key (không có `plain_key`)

### Create API key

- `POST /admin/api-keys`
- Body:
  - `client_name` (required)
  - `scopes` (required, array)
  - `rate_limit_per_day` (optional, int; fallback `APIKEY_RATE_LIMIT_PER_DAY_DEFAULT`)
- Response `201`: trả thêm `plain_key` (chỉ xuất hiện 1 lần)

### Disable API key

- `POST /admin/api-keys/{key_id}/disable`
- Response: `{"status":"ok"}`

## Templates (JWT required)

### List templates

- `GET /templates?approved=1|0`
- Response: list templates

### Create template

- `POST /templates`
- Body:
  - `name` (required)
  - `content` (required)
  - `variables` (optional; nếu không có sẽ auto extract từ content)
  - `description` (optional)
- Response `201`: template (mặc định `approved=false`)

### Update template

- `PUT /templates/{template_id}`
- Body (partial):
  - `name`, `content`, `variables`, `description`
  - Nếu update `content` thì template sẽ bị set `approved=false` và recompute `variables` (nếu không truyền `variables`).

### Approve template

- `POST /templates/{template_id}/approve`
- Response: template với `approved=true`

## SMS requests/messages (API key hoặc JWT tùy endpoint)

### Create request (API key scope `sms:send`)

- `POST /requests`
- Headers: `X-API-Key: ...`
- Body:
  - `template_id` (required)
  - `messages` (required, array; tối đa `MAX_RECIPIENTS_PER_REQUEST`)
    - mỗi item:
      - `to` (required; sẽ normalize)
      - `variables` (optional; merge với `variables` ở root)
      - `schedule_at` (optional ISO8601; nếu không có tz sẽ coi UTC)
      - `priority` (optional `HIGH|NORMAL|LOW`)
  - `variables` (optional object; default vars cho mọi message)
  - `priority` (optional `HIGH|NORMAL|LOW`; default cho message nếu message không set)
  - `metadata` (optional)
- Logic:
  - Template phải `approved=true`.
  - Chống trùng gần đây: nếu cùng `to` + `text` trong cửa sổ `ANTI_DUP_MINUTES` → message bị `CANCELED` và `last_error=DUPLICATE_RECENT`.
  - Rate limit theo ngày: nếu `usage_today + accepted > rate_limit_per_day` → `429`.
- Response `201`:
  - `{"request_id":"...","total_created":<accepted>,"total_skipped":<duplicate_count>}`

### Request detail (JWT hoặc API key scope `sms:read`)

- `GET /requests/{request_id}`
- Nếu dùng API key: chỉ xem được request của chính API key đó (khác → `403`).
- Response:
  - `{"request_id":"...","template_id":"...","total_created":...,"total_skipped":...,"created_at":"...","status_counts":{"PENDING":1,...}}`

### List messages (JWT hoặc API key scope `sms:read`)

- `GET /messages?request_id=...&status=...&limit=50&skip=0`
- `request_id` là bắt buộc.
- Response:
  - `{"items":[...], "count": <len>}`

Message object:

```json
{
  "message_id": "…",
  "request_id": "…",
  "to": "+8490…",
  "status": "PENDING|ASSIGNED|SENDING|SENT|DELIVERED|FAILED|CANCELED",
  "priority": "HIGH|NORMAL|LOW",
  "priority_weight": 0,
  "schedule_at": "2026-02-19T00:00:00Z",
  "lease_until": null,
  "agent_id": null,
  "last_error": null,
  "created_at": "…",
  "updated_at": "…"
}
```

## Agent (agent token)

### Register / rotate token

- `POST /agent/register`
- Auth: không bắt buộc; nếu gửi `Authorization: Bearer <agent_token>` thì sẽ update agent hiện tại.
- Body:
  - `device_id` (required)
  - `label` (optional)
  - `capabilities` (optional)
  - `rate_limit_per_min` (optional)
  - `registration_secret` (optional; nếu `AGENT_REGISTRATION_SECRET` được bật)
  - `rotate_token` (optional true/1/"true") cho trường hợp device_id đã tồn tại
- Response:
  - new: `201 {"status":"ok","agent_id":"...","agent_token":"..."}`
  - exists: `200 {"status":"exists","agent_id":"..."}`
  - rotated: `200 {"status":"rotated","agent_id":"...","agent_token":"..."}`

### Heartbeat

- `POST /agent/heartbeat` (agent token required)
- Body: `status?`, `battery_level?`, `app_version?`
- Response: `{"status":"ok"}`

### Lease jobs

- `GET /agent/jobs/next?limit=50` (agent token required; max 200)
- Response:
  - `{"batch_id":"...","lease_seconds":<int>,"rate_limit_per_min":<int>,"messages":[{"message_id":"...","to":"...","text":"...","priority":"...","schedule_at":"..."}]}`

### Report results

- `POST /agent/messages/report` (agent token required)
- Body:
  - `{"messages":[{"message_id":"...","status":"SENT|FAILED|DELIVERED|...","last_error":"..."}]}`
- Response: `{"updated": <int>}`

Ghi chú: server chỉ chấp nhận một số transition status (ví dụ `PENDING→ASSIGNED/SENDING/SENT/FAILED`, `SENT→DELIVERED`, ...).

## Reports (JWT required)

### Summary

- `GET /reports/summary?from=<iso>&to=<iso>&template_id=<id>`
- Response: `[{ "date":"YYYY-MM-DD", "total": 0, "sent": 0, "delivered": 0, "failed": 0 }, ...]`

### Export CSV

- `GET /reports/export.csv?from=<iso>&to=<iso>&template_id=<id>`
- Response: `text/csv` (download `reports.csv`)

