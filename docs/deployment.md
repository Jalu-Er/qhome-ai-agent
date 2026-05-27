# Deployment Guide

Panduan ini untuk menjalankan QHome AI Agent sebagai public demo di Ubuntu/LXC dengan domain sendiri.

## Target Arsitektur

```text
Internet
  -> Domain DNS
  -> Nginx reverse proxy :80/:443
  -> QHome AI Agent app 127.0.0.1:8000
```

Customer chat dibuka untuk publik di `/`. Staff dashboard dan API staff sebaiknya dilindungi Basic Auth.

## 1. Clone Project

```bash
cd /opt
sudo git clone https://github.com/Jalu-Er/qhome-ai-agent.git
sudo chown -R $USER:$USER qhome-ai-agent
cd qhome-ai-agent
```

## 2. Environment

```bash
cp .env.example .env
nano .env
```

Isi:

```bash
AI_API_KEY=sk-...
AI_BASE_URL=https://ai.sumopod.com/v1
AI_MODEL=gpt-4o-mini
```

Untuk demo hemat token, customer page dapat tetap memakai mode `Demo`. Untuk demo live, pilih `Live`.

## 3. Test Lokal

```bash
python3 run.py web --host 127.0.0.1 --port 8000
```

Buka dari server:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/staff
```

## 4. systemd Service

Buat service:

```bash
sudo nano /etc/systemd/system/qhome-ai-agent.service
```

Isi:

```ini
[Unit]
Description=QHome AI Agent Web Demo
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/qhome-ai-agent
ExecStart=/usr/bin/python3 /opt/qhome-ai-agent/run.py web --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
User=www-data
Group=www-data
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Pastikan `www-data` bisa membaca project:

```bash
sudo chown -R www-data:www-data /opt/qhome-ai-agent
```

Start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now qhome-ai-agent
sudo systemctl status qhome-ai-agent
```

## 5. Nginx Reverse Proxy

Install Nginx:

```bash
sudo apt update
sudo apt install nginx apache2-utils
```

Buat Basic Auth untuk staff:

```bash
sudo htpasswd -c /etc/nginx/.qhome-staff staff
```

Buat config:

```bash
sudo nano /etc/nginx/sites-available/qhome-ai-agent
```

Isi, ganti `agent.example.com` dengan domain:

```nginx
server {
    listen 80;
    server_name agent.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /staff {
        auth_basic "QHome Staff";
        auth_basic_user_file /etc/nginx/.qhome-staff;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ~ ^/api/(sessions|session|session/update) {
        auth_basic "QHome Staff";
        auth_basic_user_file /etc/nginx/.qhome-staff;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/qhome-ai-agent /etc/nginx/sites-enabled/qhome-ai-agent
sudo nginx -t
sudo systemctl reload nginx
```

## 6. HTTPS

Jika domain sudah mengarah ke server:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d agent.example.com
```

## 7. DNS

Arahkan domain/subdomain ke IP publik server:

```text
agent.example.com  A  <SERVER_PUBLIC_IP>
```

Jika server berada di laptop/LXC rumah, pastikan:

- Port forwarding router untuk `80` dan `443` ke host.
- LXC menerima traffic dari host.
- Firewall membuka `80` dan `443`.

## Production Limitations

MVP ini cukup untuk public demo, tetapi belum production-ready penuh:

- Session store masih in-memory, hilang saat service restart.
- Belum ada login aplikasi internal; proteksi staff direkomendasikan lewat Nginx Basic Auth.
- Belum ada upload file.
- Belum ada integrasi WhatsApp/CRM.
- Belum ada database ticket permanen.

Untuk implementasi lebih matang, langkah berikutnya adalah menambahkan SQLite/MariaDB untuk session persistence, auth staff, dan integrasi kanal kontak seperti WhatsApp atau email.
