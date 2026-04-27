#!/bin/bash
# node-secure (192.168.56.30)
# Начальный уровень зрелости: MEDIUM
# Состояние: HTTPS есть, root-доступ запрещён, firewall активен
#            НО: парольная аутентификация SSH разрешена (нарушение)

set -e

# --- Пользователь для аудита ---
id -u demo &>/dev/null || useradd -m -s /bin/bash demo
echo "demo:demo" | chpasswd
usermod -aG sudo demo
echo 'demo ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/demo-nopasswd
chmod 440 /etc/sudoers.d/demo-nopasswd

# --- Пакеты ---
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -q nginx openssl ufw

# --- Самоподписанный TLS-сертификат ---
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/server.key \
  -out    /etc/nginx/ssl/server.crt \
  -subj   "/C=RU/ST=Moscow/L=Moscow/O=Demo/CN=node-secure" \
  2>/dev/null

# --- Nginx: HTTP → redirect → HTTPS ---
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

# --- SSH: частично защищён ---
# Root-доступ запрещён, но парольная аутентификация разрешена (нарушение!)
sed -i '/^PermitRootLogin/d'        /etc/ssh/sshd_config
sed -i '/^PasswordAuthentication/d' /etc/ssh/sshd_config
echo "PermitRootLogin no"          >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >  /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

# --- Firewall: активен ---
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp

echo "[node-secure] provisioning done: MEDIUM state configured"
