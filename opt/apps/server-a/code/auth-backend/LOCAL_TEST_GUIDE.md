# Hướng dẫn chạy test AUTH-BACKEND trên local

## Yêu cầu
- Python 3.11
- pip
- MongoDB (không cần cho test, đã dùng mongomock)
- Đã clone repo và cd vào thư mục `opt/apps/server-a/code/auth-backend`

## Thiết lập môi trường
1. Tạo virtualenv:
   ```bash
   python -m venv .venv
   ```
2. Kích hoạt virtualenv:
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Ubuntu/macOS:
     ```bash
     source .venv/bin/activate
     ```
3. Cài đặt dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Chạy test
```bash
python manage.py test
```

## Lưu ý
- Test sử dụng mongomock, không cần MongoDB thật.
- Nếu gặp cảnh báo về JWT secret, hãy đặt biến môi trường `JWT_SECRET_KEY` dài hơn 32 ký tự.
- Kết quả test sẽ hiển thị OK nếu mọi thứ hợp lệ.

## Tham khảo
- Để chạy test cho các module khác, hãy kiểm tra README của từng module.
