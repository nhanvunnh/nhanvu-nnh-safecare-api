# Hướng dẫn triển khai AUTH-BACKEND trên Ubuntu

## Yêu cầu
- Ubuntu 20.04+ (hoặc tương đương)
- Python 3.11
- pip
- MongoDB (chạy thật)
- Docker & docker-compose (nếu dùng container)
- Đã clone repo vào server

## Thiết lập môi trường
1. Cài đặt Python, pip, MongoDB:
   ```bash
   sudo apt update
   sudo apt install python3.11 python3.11-venv python3-pip mongodb
   ```
2. Tạo virtualenv và cài dependencies:
   ```bash
   cd opt/apps/server-a/code/auth-backend
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Tạo file `.env` theo mẫu:
   ```env
   JWT_SECRET_KEY=your-long-secret
   MONGO_URI=mongodb://localhost:27017/auth
   COOKIE_DOMAIN=.yourdomain.com
   # ...các biến OAuth, email, v.v.
   ```

## Khởi chạy dịch vụ
- Chạy trực tiếp:
  ```bash
  python manage.py create_indexes
  python manage.py seed_defaults
  gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
  ```
- Hoặc dùng docker-compose:
  ```bash
  cd ../../services/auth
  docker-compose -f docker-compose.prod.yml up -d
  ```

## Kiểm tra
- Truy cập API qua Nginx Proxy Manager hoặc trực tiếp port 8000.
- Kiểm tra logs:
  ```bash
  tail -f /var/log/auth-backend.log
  ```

## Lưu ý
- Đảm bảo MongoDB và các biến môi trường đã cấu hình đúng.
- OAuth cần cấu hình callback URL hợp lệ.
- Để test production, dùng lệnh `python manage.py test` (cần mongomock).

## Tham khảo
- Xem README và LOCAL_TEST_GUIDE.md để biết thêm chi tiết.
