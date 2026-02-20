# Hướng dẫn triển khai `nhanvu-nnh-safecare-api` lên AWS Lightsail (Ubuntu)

Tài liệu này hướng dẫn triển khai stack Server A cho domain `api.safecare.vn` trên Lightsail Ubuntu, bao gồm:

- Cài Docker/Docker Compose.
- Clone + đồng bộ code từ GitHub **không hỏi password** (SSH deploy key).
- Cấu hình domain `api.safecare.vn` trỏ về server.
- Cấu hình SSL (Let’s Encrypt) qua Nginx Proxy Manager (NPM).
- Gợi ý tự động deploy khi push (GitHub Actions) hoặc tự động `git pull` theo timer.

## 0) Chuẩn bị trên Lightsail

1. Tạo instance Ubuntu (khuyến nghị 22.04/24.04).
2. Gán **Static IP** cho instance.
3. Mở firewall ở Lightsail (Networking):
   - TCP `80`, `443` (public)
   - TCP `81` (NPM admin) **chỉ whitelist IP quản trị** nếu có thể
   - SSH `22` (chỉ whitelist IP quản trị)

> Nếu Lightsail UI không whitelist được theo IP cho từng port, hãy dùng `ufw` ở bước bên dưới để hạn chế `81/22`.

## 1) Cấu hình DNS cho `api.safecare.vn`

Tại nơi quản lý DNS của domain `safecare.vn`:

- Tạo bản ghi `A`:
  - Name/Host: `api`
  - Value: `<STATIC_IP_CỦA_LIGHTSAIL>`
  - TTL: 300–600s

Chờ DNS propagate, kiểm tra:

```bash
dig +short api.safecare.vn
```

## 2) Update OS + cài Docker / Compose

SSH vào server:

```bash
ssh ubuntu@<STATIC_IP>
```

Update:

```bash
sudo apt-get update
sudo apt-get -y upgrade
sudo reboot
```

SSH lại và cài Docker theo hướng dẫn chính thức (khuyến nghị) hoặc dùng gói Ubuntu.

### Cách khuyến nghị: Docker Engine + Compose plugin

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Cho user chạy docker không cần sudo:

```bash
sudo usermod -aG docker $USER
newgrp docker
docker version
docker compose version
```

## 3) (Khuyến nghị) Bật UFW và giới hạn port quản trị

```bash
sudo apt-get install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw allow 81/tcp
sudo ufw enable
sudo ufw status verbose
```

Nếu muốn whitelist IP quản trị cho SSH và NPM UI:

```bash
ADMIN_IP="<IP_CỦA_BẠN>/32"
sudo ufw delete allow 22/tcp
sudo ufw delete allow 81/tcp
sudo ufw allow from "$ADMIN_IP" to any port 22 proto tcp
sudo ufw allow from "$ADMIN_IP" to any port 81 proto tcp
sudo ufw status numbered
```

## 4) Clone repo GitHub bằng SSH (không hỏi pass)

### 4.1 Tạo deploy key trên server

Tạo key chỉ dùng cho repo này:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh

ssh-keygen -t ed25519 -C "lightsail-safecare-api" -f ~/.ssh/id_ed25519_safecare_api
```

In public key:

```bash
cat ~/.ssh/id_ed25519_safecare_api.pub
```

### 4.2 Add deploy key vào GitHub

Trên GitHub repo:

- Settings → Deploy keys → Add deploy key
- Paste public key ở trên
- Tick **Allow write access** chỉ khi bạn cần push từ server (thường không cần).

### 4.3 Cấu hình SSH để git tự dùng key này

Tạo `~/.ssh/config`:

```bash
cat > ~/.ssh/config <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_safecare_api
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
```

Add `known_hosts` để không bị prompt:

```bash
ssh-keyscan -H github.com >> ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts
```

Test:

```bash
ssh -T git@github.com
```

### 4.4 Clone repo

Chọn thư mục deploy (ví dụ `/opt`):

```bash
sudo mkdir -p /opt/apps
sudo chown -R "$USER":"$USER" /opt/apps

cd /opt/apps
git clone git@github.com:<ORG_OR_USER>/<REPO>.git nhanvu-nnh-safecare-api
cd nhanvu-nnh-safecare-api
```

## 5) Chuẩn bị biến môi trường (secrets)

File quan trọng:

- `opt/apps/server-a/infra/.env.infra` (Mongo/Redis + password)
- `opt/apps/server-a/services/auth/.env`, `opt/apps/server-a/services/sms/.env`, ... (env từng service)

Trên server, **không commit** các file `.env` production. Bạn tạo/điền trực tiếp trên máy:

```bash
cd /opt/apps/nhanvu-nnh-safecare-api

cp opt/apps/server-a/infra/.env.infra opt/apps/server-a/infra/.env.infra.local 2>/dev/null || true
```

Khuyến nghị: dùng đúng tên file mà compose/script đang đọc:

- infra: `opt/apps/server-a/infra/.env.infra`
- services: `opt/apps/server-a/services/<name>/.env`

## 6) Tạo Docker networks external

```bash
docker network create proxy-network || true
docker network create infra-network || true
```

## 7) Deploy infrastructure (NPM + Mongo + Redis)

Infra compose nằm tại:

- `opt/apps/server-a/service/docker-compose.prod.yml`

Chạy:

```bash
cd /opt/apps/server-a/service
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

Kiểm tra Mongo init user:

```bash
cd /opt/apps/server-a/service
docker compose -f docker-compose.prod.yml logs --tail 200 shared_mongo
```

## 8) Deploy services (auth, sms, ...)

Service compose production đang ở:

- `opt/apps/server-a/services/docker-compose.prod.yml`

Chạy:

```bash
cd /opt/apps/nhanvu-nnh-safecare-api/opt/apps/server-a/services
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

Test health nội bộ:

```bash
docker compose -f docker-compose.prod.yml exec -T auth sh -lc "curl -fsS -H 'Host: api.safecare.vn' http://localhost:8000/health && echo"
docker compose -f docker-compose.prod.yml exec -T sms  sh -lc "curl -fsS -H 'Host: api.safecare.vn' http://localhost:8000/health && echo"
```

## 9) Cấu hình Nginx Proxy Manager (domain + SSL)

Mở NPM admin:

- `http://<STATIC_IP>:81`

### 9.1 Tạo Proxy Host cho `api.safecare.vn`

- Domain Names: `api.safecare.vn`
- Scheme: `http`
- Forward Hostname / IP:
  - Có thể trỏ tạm đến `svc_core` hoặc bất kỳ service mặc định (nếu bạn dùng Custom Locations).
- Forward Port: `8000`

### 9.2 Custom Locations (path-based)

Thêm các location (ví dụ):

- `/auth` → `svc_auth:8000`
- `/sms`  → `svc_sms:8000`
- `/shop` → `svc_shop:8000`
- `/laydi` → `svc_laydi:8000`
- `/core` → `svc_core:8000`

Nếu backend không tự handle prefix, thêm rule rewrite ở Advanced (ví dụ auth):

```nginx
rewrite ^/auth/(.*)$ /$1 break;
rewrite ^/sms/(.*)$ /$1 break;
```

### 9.3 SSL Let’s Encrypt

Tab SSL:

- Request a new SSL Certificate
- Agree Let’s Encrypt TOS
- Force SSL: ON
- HTTP/2 Support: ON

Sau khi cấp xong, test:

```bash
curl -i https://api.safecare.vn/auth/health
curl -i https://api.safecare.vn/sms/health
```

## 10) Tự động đồng bộ code (không hỏi pass)

Bạn có 2 hướng phổ biến:

### A) GitHub Actions deploy qua SSH (khuyến nghị)

Ưu điểm: deploy ngay khi push, không cần mở webhook/service nhận request trên server.

Ý tưởng:

1. Tạo SSH key cho GitHub Actions (khác với deploy key ở server).
2. Add public key vào `~/.ssh/authorized_keys` của server.
3. Lưu private key vào GitHub repo secrets (ví dụ `LIGHTSAIL_SSH_KEY`).
4. Workflow SSH vào server và chạy:
   - `git pull`
   - `docker compose up -d --build`

### B) Systemd timer tự `git pull` mỗi N phút

Tạo file service:

```bash
sudo tee /etc/systemd/system/safecare-sync.service > /dev/null <<'EOF'
[Unit]
Description=Sync SafeCare API repo

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/opt/apps/nhanvu-nnh-safecare-api
ExecStart=/usr/bin/git pull --rebase
EOF
```

Tạo timer (ví dụ 2 phút/lần):

```bash
sudo tee /etc/systemd/system/safecare-sync.timer > /dev/null <<'EOF'
[Unit]
Description=Run SafeCare sync periodically

[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
Unit=safecare-sync.service

[Install]
WantedBy=timers.target
EOF
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now safecare-sync.timer
systemctl list-timers --all | grep safecare-sync
```

> Sau khi sync code, bạn vẫn cần cơ chế redeploy container (có thể tạo thêm service/timer `docker compose up -d --build` hoặc trigger theo tag/commit).

## 11) Troubleshooting nhanh

- Xem log:
  - `docker compose -f opt/apps/server-a/services/docker-compose.prod.yml logs -f auth`
  - `docker compose -f opt/apps/server-a/services/docker-compose.prod.yml logs -f sms`
  - `docker logs -f npm`
- Nếu SSL fail: kiểm tra port 80/443 có mở và DNS A record đúng IP.
- Nếu Django trả `400 Bad Request`: thường do `ALLOWED_HOSTS`/header Host; kiểm tra config NPM forwarding headers.

