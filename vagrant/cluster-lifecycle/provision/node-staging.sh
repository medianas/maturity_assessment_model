#!/bin/bash
# node-staging (192.168.57.20)
# STAGING: HTTPS есть, SSH полу-настроен, ufw активен
# Цель — промежуточное окружение, готовится к production

set -e

# --- Demo-пользователь ---
id -u demo &>/dev/null || useradd -m -s /bin/bash demo
echo "demo:demo" | chpasswd
usermod -aG sudo demo
echo 'demo ALL=(ALL) NOPASSWD: /usr/sbin/ufw' > /etc/sudoers.d/demo-ufw
chmod 440 /etc/sudoers.d/demo-ufw

# --- Пакеты ---
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -q nginx openssl ufw

# --- Self-signed TLS-сертификат ---
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/server.key \
  -out    /etc/nginx/ssl/server.crt \
  -subj   "/C=RU/ST=Moscow/L=Moscow/O=Demo/CN=node-staging" \
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
    root /var/www/html;
    index index.html;
    server_name _;
    location / { try_files $uri $uri/ =404; }
}
EOF
systemctl enable nginx
systemctl restart nginx

# --- SSH: PermitRootLogin no, но PasswordAuth yes (полу-настроен) ---
sed -i '/^PermitRootLogin/d'        /etc/ssh/sshd_config
sed -i '/^PasswordAuthentication/d' /etc/ssh/sshd_config
echo "PermitRootLogin no"          >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >  /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

# --- Firewall активен (но без явных правил для веб-портов — ufw default) ---
ufw --force enable
ufw allow ssh

echo "[node-staging] provisioned: STAGING state — HTTPS, semi-hardened SSH, ufw active"
