# SMS Module API (sms-backend)

Backend URL cá»‘ Ä‘á»‹nh:

- Dev: `http://192.168.1.5:8090`
- Prod: `https://api.safecare.vn`

CÃ¡c endpoint dÆ°á»›i Ä‘Ã¢y lÃ  Ä‘Æ°á»ng dáº«n **táº¡i root cá»§a service**. Khi Ä‘i qua Nginx Proxy Manager (path-based routing), thÆ°á»ng sáº½ map dÆ°á»›i prefix `/sms`, vÃ­ dá»¥: `/sms/health`, `/sms/templates`, ...

## Authentication

SMS backend há»— trá»£ 3 kiá»ƒu principal:

1) **JWT user** (cho admin/operator):
   - Header: `Authorization: Bearer <jwt>` (token cÃ³ dáº¥u `.`)
   - DÃ¹ng cho: templates, reports, quáº£n lÃ½ API key.

2) **API Key principal** (cho client gá»­i/tra cá»©u SMS):
   - Header: `X-API-Key: <plain_key>`
   - Scopes:
     - `sms:send` (gá»­i)
     - `sms:read` (xem request/messages)

3) **Agent principal** (cho thiáº¿t bá»‹/agent gá»­i tin):
   - Header: `Authorization: Bearer <agent_token>` (token **khÃ´ng** cÃ³ dáº¥u `.`)
   - DÃ¹ng cho: agent/*.

## Health

- `GET /health` â†’ `200 {"status":"ok"}`

## Admin: API keys (JWT required)

### List API keys

- `GET /admin/api-keys`
- Response: danh sÃ¡ch key (khÃ´ng cÃ³ `plain_key`)

### Create API key

- `POST /admin/api-keys`
- Body:
  - `client_name` (required)
  - `scopes` (required, array)
  - `rate_limit_per_day` (optional, int; fallback `APIKEY_RATE_LIMIT_PER_DAY_DEFAULT`)
- Response `201`: tráº£ thÃªm `plain_key` (chá»‰ xuáº¥t hiá»‡n 1 láº§n)

### Disable API key

- `POST /admin/api-keys/{key_id}/disable`
- Response: `{"status":"ok"}`

### List registered agents/devices

- `GET /admin/agents` (JWT required)
- Query (optional):
  - `is_active=1|0|true|false`
- Response:
  - `{"items":[{"agent_id":"...","device_id":"...","label":"...","is_active":true,"last_seen_at":"..."}], "count": 1}`

### Unregister/deactivate device

- `POST /admin/agents/{agent_id}/unregister` (JWT required)
- Body (optional):
  - `reason` (string)
- Response:
  - `{"status":"ok","agent":{...}}`

### Get registration secret

- `GET /admin/agent/registration-secret` (JWT required)
- Response:
  - `{"registration_secret":"...","configured":true}`

### Create/update registration secret

- `PUT /admin/agent/registration-secret` (JWT required)
- Body:
  - `registration_secret` (required, string; send empty string to disable)
- Response:
  - `{"status":"ok","registration_secret":"...","configured":true}`

## Templates (JWT required)

### List templates

- `GET /templates?approved=1|0`
- Response: list templates

### Create template

- `POST /templates`
- Body:
  - `name` (required)
  - `content` (required)
  - `variables` (optional; náº¿u khÃ´ng cÃ³ sáº½ auto extract tá»« content)
  - `description` (optional)
- Response `201`: template (máº·c Ä‘á»‹nh `approved=false`)

### Update template

- `PUT /templates/{template_id}`
- Body (partial):
  - `name`, `content`, `variables`, `description`
  - Náº¿u update `content` thÃ¬ template sáº½ bá»‹ set `approved=false` vÃ  recompute `variables` (náº¿u khÃ´ng truyá»n `variables`).

### Approve template

- `POST /templates/{template_id}/approve`
- Response: template vá»›i `approved=true`

## SMS requests/messages (API key hoáº·c JWT tÃ¹y endpoint)

### Create request (API key scope `sms:send`)

- `POST /requests`
- Headers: `X-API-Key: ...`
- Body:
  - `template_id` (required)
  - `agent_id` (required; ObjectId cua agent nhan job)
  - `messages` (required, array; tá»‘i Ä‘a `MAX_RECIPIENTS_PER_REQUEST`)
    - má»—i item:
      - `to` (required; sáº½ normalize)
      - `variables` (optional; merge vá»›i `variables` á»Ÿ root)
      - `schedule_at` (optional ISO8601; náº¿u khÃ´ng cÃ³ tz sáº½ coi UTC)
      - `priority` (optional `HIGH|NORMAL|LOW`)
  - `variables` (optional object; default vars cho má»i message)
  - `priority` (optional `HIGH|NORMAL|LOW`; default cho message náº¿u message khÃ´ng set)
  - `metadata` (optional)
- Logic:
  - Template pháº£i `approved=true`.
  - Chá»‘ng trÃ¹ng gáº§n Ä‘Ã¢y: náº¿u cÃ¹ng `to` + `text` trong cá»­a sá»• `ANTI_DUP_MINUTES` â†’ message bá»‹ `CANCELED` vÃ  `last_error=DUPLICATE_RECENT`.
  - Rate limit theo ngÃ y: náº¿u `usage_today + accepted > rate_limit_per_day` â†’ `429`.
- Response `201`:
  - `{"request_id":"...","agent_id":"...","total_created":<accepted>,"total_skipped":<duplicate_count>}`

### Request detail (JWT hoáº·c API key scope `sms:read`)

- `GET /requests/{request_id}`
- Náº¿u dÃ¹ng API key: chá»‰ xem Ä‘Æ°á»£c request cá»§a chÃ­nh API key Ä‘Ã³ (khÃ¡c â†’ `403`).
- Response:
  - `{"request_id":"...","template_id":"...","total_created":...,"total_skipped":...,"created_at":"...","status_counts":{"PENDING":1,...}}`

### List messages (JWT hoáº·c API key scope `sms:read`)

- `GET /messages?request_id=...&status=...&limit=50&skip=0`
- `request_id` lÃ  báº¯t buá»™c.
- Response:
  - `{"items":[...], "count": <len>}`

### List all messages (JWT hoáº·c API key scope `sms:read`)

- `GET /messages/all?status=...&request_id=...&agent_id=...&to=...&limit=50&skip=0`
- CÃ¡c query param lÃ  tÃ¹y chá»n.
- Náº¿u dÃ¹ng API key: chá»‰ nhÃ¬n tháº¥y tin nháº¯n cá»§a API key Ä‘Ã³.
- Response:
  - `{"items":[...], "count": <len>}`

Message object:

```json
{
  "message_id": "â€¦",
  "request_id": "â€¦",
  "to": "+8490â€¦",
  "status": "PENDING|ASSIGNED|SENDING|SENT|DELIVERED|FAILED|CANCELED",
  "priority": "HIGH|NORMAL|LOW",
  "priority_weight": 0,
  "schedule_at": "2026-02-19T00:00:00Z",
  "lease_until": null,
  "agent_id": null,
  "last_error": null,
  "created_at": "â€¦",
  "updated_at": "â€¦"
}
```

## Agent (agent token)

### Register / rotate token

- `POST /agent/register`
- Auth: khÃ´ng báº¯t buá»™c; náº¿u gá»­i `Authorization: Bearer <agent_token>` thÃ¬ sáº½ update agent hiá»‡n táº¡i.
- Body:
  - `device_id` (required)
  - `label` (optional)
  - `capabilities` (optional)
  - `rate_limit_per_min` (optional)
  - `registration_secret` (optional; náº¿u `AGENT_REGISTRATION_SECRET` Ä‘Æ°á»£c báº­t)
  - `rotate_token` (optional true/1/"true") cho trÆ°á»ng há»£p device_id Ä‘Ã£ tá»“n táº¡i
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
- Server chi lease message co `agent_id` trung voi agent dang goi.
- Response:
  - `{"batch_id":"...","lease_seconds":<int>,"rate_limit_per_min":<int>,"messages":[{"message_id":"...","to":"...","text":"...","priority":"...","schedule_at":"..."}]}`

### Report results

- `POST /agent/messages/report` (agent token required)
- Body:
  - `{"messages":[{"message_id":"...","status":"SENT|FAILED|DELIVERED|...","last_error":"..."}]}`
- Response: `{"updated": <int>}`

Ghi chÃº: server chá»‰ cháº¥p nháº­n má»™t sá»‘ transition status (vÃ­ dá»¥ `PENDINGâ†’ASSIGNED/SENDING/SENT/FAILED`, `SENTâ†’DELIVERED`, ...).

## Reports (JWT required)

### Summary

- `GET /reports/summary?from=<iso>&to=<iso>&template_id=<id>`
- Response: `[{ "date":"YYYY-MM-DD", "total": 0, "sent": 0, "delivered": 0, "failed": 0 }, ...]`

### Export CSV

- `GET /reports/export.csv?from=<iso>&to=<iso>&template_id=<id>`
- Response: `text/csv` (download `reports.csv`)

