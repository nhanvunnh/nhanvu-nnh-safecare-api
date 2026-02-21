# SafeCare Image Service API Guide

Image service exposes compatible endpoints under prefix `/image`.

Base URL examples:
- Prod: `https://api.safecare.vn/image`
- Local: `http://localhost:8000`

## Endpoints

- `GET /health`
- `GET /get_image`
- `GET /good_image`
- `POST /drive/upload`
- `POST /drive/delete`
- `POST /s3/upload`
- `POST /s3/delete`

## 1) Health Check

`GET /health`

Response:

```json
{"status":"ok"}
```

Example:

```bash
curl "https://api.safecare.vn/image/health"
```

## 2) Get GNH Image (Drive)

`GET /get_image?file=<filename>&w=<optional_width>`

- `file`: filename in Drive folder `GNH_IMAGES_DRIVE_FOLDER_ID`
- `w`: optional resize width (px), e.g. `240`

Example:

```bash
curl -L "https://api.safecare.vn/image/get_image?file=GNH_20260220_001.jpg&w=640" -o gnh.jpg
```

## 3) Get Good Image (Drive/S3/Local)

`GET /good_image?file=<path>&w=<optional_width>`

`file` supports:
- Drive: `drive:good_67bc1234_demo.jpg`
- S3 URL: `https://safeappbucket.s3.amazonaws.com/good/123/a.jpg`
- Local path: `good/123/a.jpg`

Examples:

```bash
curl -L "https://api.safecare.vn/image/good_image?file=drive:good_67bc1234_demo.jpg&w=320" -o good_drive.jpg
curl -L "https://api.safecare.vn/image/good_image?file=https://safeappbucket.s3.amazonaws.com/good/123/a.jpg" -o good_s3.jpg
curl -L "https://api.safecare.vn/image/good_image?file=good/123/a.jpg" -o good_local.jpg
```

## 4) Upload to Drive

`POST /drive/upload`

Supported input:
- `multipart/form-data` with file field `file`
- JSON with base64: `content_base64`, `filename`, optional `mime_type`

Body fields:
- `folder_id` (optional): defaults to `GOOD_IMAGES_DRIVE_FOLDER_ID`
- `drive_name` (optional): name to save in Drive
- `filename` (required for base64 mode)

### 4.1 Multipart example

```bash
curl -X POST "https://api.safecare.vn/image/drive/upload" \
  -F "file=@./sample.jpg" \
  -F "folder_id=1TEq-SOHKylWpsIXXMRLXOSK8ofoIhvMQ" \
  -F "drive_name=good_67bc1234_sample.jpg"
```

Sample response:

```json
{
  "status": "ok",
  "drive": {
    "id": "1AbCdEfGhIjKlMn",
    "name": "good_67bc1234_sample.jpg"
  },
  "path": "drive:good_67bc1234_sample.jpg"
}
```

### 4.2 JSON base64 example

```bash
curl -X POST "https://api.safecare.vn/image/drive/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "1TEq-SOHKylWpsIXXMRLXOSK8ofoIhvMQ",
    "filename": "sample.jpg",
    "drive_name": "good_67bc1234_sample.jpg",
    "mime_type": "image/jpeg",
    "content_base64": "<BASE64_DATA>"
  }'
```

## 5) Delete from Drive

`POST /drive/delete`

Body:
- `folder_id` (optional): default `GOOD_IMAGES_DRIVE_FOLDER_ID`
- `filename` or `path` (supports `drive:<name>`)

Example:

```bash
curl -X POST "https://api.safecare.vn/image/drive/delete" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "1TEq-SOHKylWpsIXXMRLXOSK8ofoIhvMQ",
    "path": "drive:good_67bc1234_sample.jpg"
  }'
```

Response:

```json
{"status":"ok"}
```

## 6) Upload to S3

`POST /s3/upload`

Supported input:
- `multipart/form-data` with file field `file`
- JSON with base64 (`content_base64`)

Body fields:
- `target_folder` (optional, default `good/misc`)
- `filename` (required for base64 mode)
- `mime_type` (optional for base64)

### 6.1 Multipart example

```bash
curl -X POST "https://api.safecare.vn/image/s3/upload" \
  -F "file=@./sample.jpg" \
  -F "target_folder=good/67bc1234"
```

Sample response:

```json
{
  "status": "ok",
  "url": "https://safeappbucket.s3.amazonaws.com/good/67bc1234/sample.jpg",
  "key": "good/67bc1234/sample.jpg"
}
```

### 6.2 JSON base64 example

```bash
curl -X POST "https://api.safecare.vn/image/s3/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "target_folder": "good/67bc1234",
    "filename": "sample.jpg",
    "mime_type": "image/jpeg",
    "content_base64": "<BASE64_DATA>"
  }'
```

## 7) Delete from S3

`POST /s3/delete`

Body:
- `url` (required, must start with configured `AWS_BUCKET`)

Example:

```bash
curl -X POST "https://api.safecare.vn/image/s3/delete" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://safeappbucket.s3.amazonaws.com/good/67bc1234/sample.jpg"
  }'
```

Response:

```json
{"status":"ok"}
```

## 8) Common Error Responses

- `400` missing required params

```json
{"detail":"filename and content required"}
```

- `502` backend provider failed

```json
{"detail":"Drive upload failed"}
```

## 9) Important Notes

- Current implementation is open (no auth layer on these endpoints).
- Drive service account file path is from env: `GOOGLE_SERVICE_ACCOUNT_FILE`.
- Cache cleanup logs are stored in Mongo collection: `image_cache_cleanup_logs`.
