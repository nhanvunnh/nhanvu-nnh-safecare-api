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

### Cài đặt Nginx Proxy Manager (nếu chưa có)
Bạn có thể chạy Nginx Proxy Manager bằng Docker riêng biệt hoặc tích hợp vào docker-compose:

- Chạy độc lập:
  ```bash
  docker volume create npm-data
  docker volume create npm-letsencrypt
  docker run -d \
    --name=nginx-proxy-manager \
    -p 80:80 \
    -p 81:81 \
    -p 443:443 \
    -v npm-data:/data \
    -v npm-letsencrypt:/etc/letsencrypt \
    --restart=always \
    jc21/nginx-proxy-manager:latest
  ```
- Hoặc thêm service `nginx-proxy-manager` vào file `docker-compose.prod.yml` nếu chưa có.

Sau khi chạy, truy cập http://localhost:81 để cấu hình proxy và SSL.
Tài khoản mặc định: 
- user: admin@example.com
- pass: changeme

### Cài đặt Redis bằng Docker (nếu chưa có)
Bạn có thể chạy Redis độc lập bằng Docker trên Windows:

```bash
# Tạo network nếu cần (nếu các service dùng chung network)
docker network create infra-network

# Chạy Redis
# Đơn giản:
docker run -d --name redis --network=infra-network -p 6379:6379 redis:7-alpine

# Nếu muốn lưu data ra ổ đĩa:
docker run -d --name redis --network=infra-network -p 6379:6379 -v redis-data:/data redis:7-alpine
```

- Redis sẽ chạy ở port 6379 (mặc định). Nếu port này bị chiếm, đổi sang port khác (ví dụ: -p 6380:6379).
- Nếu dùng docker-compose, chỉ cần đảm bảo service redis đã có trong file compose.
- Để kiểm tra Redis đã chạy:
```bash
docker ps
```
- Để truy cập redis-cli:
```bash
docker exec -it redis redis-cli
```

### Cài đặt MongoDB bằng Docker (nếu chưa có)
Bạn có thể chạy MongoDB độc lập bằng Docker trên Windows:

```bash
# Tạo network nếu cần (nếu các service dùng chung network)
docker network create infra-network

# Chạy MongoDB
# Đơn giản:
docker run -d --name mongo --network=infra-network -p 27017:27017 mongo:6-jammy

# Nếu muốn lưu data ra ổ đĩa:
docker run -d --name mongo --network=infra-network -p 27017:27017 -v mongo-data:/data/db mongo:6-jammy
```

- MongoDB sẽ chạy ở port 27017 (mặc định). Nếu port này bị chiếm, đổi sang port khác (ví dụ: -p 27018:27017).
- Nếu dùng docker-compose, chỉ cần đảm bảo service mongo đã có trong file compose.
- Để kiểm tra MongoDB đã chạy:
```bash
docker ps
```
- Để truy cập mongo shell:
```bash
docker exec -it mongo mongosh
```

### Reset dữ liệu Mongo (xóa volume)
- **Cảnh báo:** thao tác này xóa toàn bộ dữ liệu Mongo (user, collection). Chỉ thực hiện khi muốn về trạng thái sạch.
- Thực hiện trên máy Windows tại thư mục `opt/apps/server-a/services`:
  ```powershell
  docker-compose -f docker-compose.prod.yml down shared_mongo
  Remove-Item -Recurse -Force ..\infra\data\mongo
  docker-compose -f docker-compose.prod.yml up -d shared_mongo
  ```
  (Nếu dùng CMD: `rd /s /q ..\infra\data\mongo`)
  ```powershell
  docker-compose -f docker-compose.prod.yml up -d auth sms svc_core svc_laydi svc_shop
  ```

  ### Kiểm tra kết nối Mongo
  - Đứng trong thư mục `opt/apps/server-a/services` và đảm bảo `shared_mongo` đang chạy.
  - Dùng lệnh sau để xác thực bằng tài khoản root (thay `root_admin`/`change-this-password` theo file `../infra/.env.infra` nếu đã chỉnh sửa):
    ```powershell
    docker compose -f docker-compose.prod.yml exec shared_mongo mongosh -u root_admin -p change-this-password --authenticationDatabase admin --eval "db.runCommand({ connectionStatus: 1 })"
    ```
  - Nếu lệnh trả về `"ok" : 1`, kết nối Mongo đã sẵn sàng. Ngược lại, kiểm tra lại biến môi trường trong `.env.infra` hoặc khởi động lại container `shared_mongo`.
  - Sau khi reset volume, cần chờ 5-10 giây để script trong `infra/mongo_init` tạo root user và các user ứng dụng. Nếu thấy lỗi `UserNotFound` hoặc `Authentication failed`, xem log `docker compose -f docker-compose.prod.yml logs shared_mongo` và chạy lại lệnh sau khi thông báo `MongoDB init process complete; ready for start up.` xuất hiện.

## Lưu ý
- Nếu gặp lỗi port, hãy kiểm tra các port đã được cấu hình trong compose và .env.
- Nếu gặp lỗi `network infra-network declared as external, but could not be found`, hãy tạo network này trước bằng lệnh:
  ```bash
  docker network create infra-network
  ```
  Sau đó chạy lại docker-compose.
- Nếu gặp cảnh báo `the attribute version is obsolete`, bạn có thể xóa dòng `version:` ở đầu file `docker-compose.prod.yml` để tránh cảnh báo (không ảnh hưởng đến việc chạy).
- Nếu gặp lỗi `network proxy-network declared as external, but could not be found`, hãy tạo network này trước bằng lệnh:
  ```bash
  docker network create proxy-network
  ```
  Sau đó chạy lại docker-compose.
- Đảm bảo Docker Desktop đã bật và có quyền truy cập file hệ thống.
- Có thể chỉnh sửa docker-compose.prod.yml để thêm/xóa module theo nhu cầu.

## Tham khảo
- Xem README và các file hướng dẫn trong từng module để biết thêm chi tiết.

### Xử lý lỗi port bị chiếm
- Nếu gặp lỗi `ports are not available: ... bind: An attempt was made to access a socket in a way forbidden by its access permissions`, nghĩa là port 80, 81 hoặc 443 đã bị chiếm (thường do IIS, Skype, WSL, Apache, ... hoặc một container khác).
  - Hãy dừng các dịch vụ chiếm port này hoặc đổi sang port khác (ví dụ: `-p 8080:80 -p 8181:81 -p 4443:443`).
  - Nếu đổi port, khi truy cập Nginx Proxy Manager dùng địa chỉ `http://localhost:8181`.
  - Để kiểm tra port nào đang bị chiếm, dùng lệnh:
    ```powershell
    netstat -ano | findstr :80
    netstat -ano | findstr :81
    netstat -ano | findstr :443
    ```
  - Sau đó có thể dừng tiến trình bằng Task Manager hoặc lệnh `taskkill /PID <pid> /F`.

### Xử lý lỗi container trùng tên
- Nếu gặp lỗi `The container name "/nginx-proxy-manager" is already in use ...`, nghĩa là container này đã tồn tại.
  - Có thể xóa container cũ bằng lệnh:
    ```bash
    docker rm -f nginx-proxy-manager
    ```
  - Sau đó chạy lại lệnh docker run.
  - Hoặc đổi tên container mới bằng cách sửa tham số `--name` (ví dụ: `--name=nginx-proxy-manager2`).

### Xử lý lỗi không tìm thấy file docker-compose.prod.yml
- Nếu gặp lỗi `open .../docker-compose.prod.yml: The system cannot find the file specified.`, hãy kiểm tra lại đường dẫn và tên file:
  - Đảm bảo bạn đang ở đúng thư mục `opt/apps/server-a/services`.
  - Đảm bảo file `docker-compose.prod.yml` tồn tại trong thư mục này.
  - Nếu chưa có, hãy copy file mẫu hoặc liên hệ quản trị viên để lấy file cấu hình đúng.
  - Kiểm tra lại lệnh và đường dẫn trước khi chạy docker-compose.
- Nếu gặp lỗi `pull access denied for your-registry/...`:
  - Đây là các image placeholder (`your-registry/core-service`, `laydi-service`, `shop-service`). Bạn cần build image local hoặc chỉnh lại `image` cho đúng registry.
  - Nếu đã có registry thật, chạy `docker login <registry>` trước khi pull.
  - Trong môi trường phát triển, có thể thay `image` bằng `build` trỏ tới source tương ứng hoặc push image lên registry private của bạn.

  docker compose -f docker-compose.prod.yml build auth sms
