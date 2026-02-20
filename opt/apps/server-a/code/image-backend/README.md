# SafeCare Image Service

Service d?c l?p ph?c v? ?nh t? Google Drive/S3/local cache, gi? endpoint tuong thích:

- `GET /image/get_image?file=<name>&w=<optional width>`
- `GET /image/good_image?file=<path_or_drive_or_url>&w=<optional width>`

Endpoint qu?n tr? upload/delete:

- `POST /image/drive/upload`
- `POST /image/drive/delete`
- `POST /image/s3/upload`
- `POST /image/s3/delete`

## Environment

Copy `.env.example` thành `.env` và c?p nh?t:

- `MONGO_URI`, `MONGO_DB`
- `GOOGLE_SERVICE_ACCOUNT_FILE`
- `GOOD_IMAGES_DRIVE_FOLDER_ID`, `GNH_IMAGES_DRIVE_FOLDER_ID`
- `ENABLE_S3`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_BUCKET`
- cache directories và quota n?u c?n

## Run local

```bash
docker compose up --build
```

## Health

`GET /image/health`
