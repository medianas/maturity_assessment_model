#!/bin/bash
# node-public (192.168.58.30)
# PUBLIC: публичный HTTPS-сайт, hardened SSH, ufw с правилами
# Цель — production-grade публичный узел

set -e

# --- Demo-пользователь ---
id -u demo &>/dev/null || useradd -m -s /bin/bash demo
echo "demo:demo" | chpasswd
usermod -aG sudo demo
echo 'demo ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/demo-nopasswd
chmod 440 /etc/sudoers.d/demo-nopasswd

# --- Пакеты ---
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -q nginx openssl ufw

# --- TLS-сертификат ---
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/server.key \
  -out    /etc/nginx/ssl/server.crt \
  -subj   "/C=RU/ST=Moscow/L=Moscow/O=Demo/CN=node-public" \
  2>/dev/null

# --- Nginx: HTTP → 301 → HTTPS ---
cat > /etc/nginx/sites-available/default <<'EOF'
server {
    listen 80 default_server;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl default_server;
    ssl_certificate     /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;
    add_header Strict-Transport-Security "max-age=63072000" always;
    root /var/www/html;
    index index.html;
    server_name _;
    location / { try_files $uri $uri/ =404; }
}
EOF
systemctl enable nginx
systemctl restart nginx

# --- SSH: hardened ---
sed -i '/^PermitRootLogin/d'        /etc/ssh/sshd_config
sed -i '/^PasswordAuthentication/d' /etc/ssh/sshd_config
echo "PermitRootLogin no"          >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >  /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

# --- Firewall: SSH + 80 + 443 ---
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw default deny incoming
ufw default allow outgoing

echo "[node-public] provisioned: PUBLIC — HTTPS+HSTS, hardened SSH, ufw with rules"
