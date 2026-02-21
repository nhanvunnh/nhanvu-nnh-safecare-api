# Sheet Sync Backend (server-a)

Service dong bo Google Sheet dung chung cho nhieu module.

## Base URL
- Public: `/sheet`
- Health: `/sheet/health`

## APIs
- `POST /sheet/apps/upsert`
- `POST /sheet/apps/get`
- `POST /sheet/apps/list`
- `POST /sheet/jobs/run`
- `POST /sheet/logs/list`

## Auth
- `api_token` scope read/write/admin, hoac
- `service_token` (for internal services)

## Bootstrap
```bash
python manage.py create_indexes
python manage.py seed_defaults
```

`seed_defaults` tao app config mac dinh cho `gnh`.
