# Hướng dẫn chạy toàn bộ Server A bằng Docker trên Windows

## Yêu cầu
- Windows 10/11
- Docker Desktop (đã cài và bật)
- Git (để clone repo)

## Các bước thực hiện

### 1. Clone repo
Nếu chưa có mã nguồn:
```bash
git clone <repo-url>
cd nhanvu-nnh-safecare-api
```

### 2. Kiểm tra cấu hình .env
- Mỗi service (auth, sms, ...) đều có file `.env` mẫu trong thư mục `opt/apps/server-a/services/<module>`.
- Copy `.env.example` thành `.env` và chỉnh sửa các biến theo môi trường thực tế (JWT, Mongo, Redis, OAuth, email, ...).

### 3. Khởi động Docker Compose
- Di chuyển đến thư mục services:
```bash
cd opt/apps/server-a/services
```
- Khởi động toàn bộ module:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Kiểm tra trạng thái các container
```bash
docker ps
```
- Đảm bảo các container như `auth`, `sms`, `mongo`, `redis`, `nginx-proxy-manager` đều đang chạy.

### 5. Truy cập API
- Các API sẽ được reverse proxy qua Nginx Proxy Manager.
- Truy cập địa chỉ: `http://localhost` hoặc domain đã cấu hình.

### 6. Xem logs
- Xem logs của một service:
```bash
docker-compose -f docker-compose.prod.yml logs <service-name>
```
- Ví dụ:
```bash
docker-compose -f docker-compose.prod.yml logs auth
```

### 7. Dừng toàn bộ module
```bash
docker-compose -f docker-compose.prod.yml down
```

## Lưu ý
- Nếu gặp lỗi port, hãy kiểm tra các port đã được cấu hình trong compose và .env.
- Đảm bảo Docker Desktop đã bật và có quyền truy cập file hệ thống.
- Có thể chỉnh sửa docker-compose.prod.yml để thêm/xóa module theo nhu cầu.

## Tham khảo
- Xem README và các file hướng dẫn trong từng module để biết thêm chi tiết.
