#!/bin/bash
# node-app (192.168.56.20)
# Начальный уровень зрелости: LOW
# Нарушения: только HTTP, слабый SSH, firewall установлен но неактивен

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
apt-get install -y -q nginx ufw

# --- Nginx: только HTTP (порт 80, HTTPS отсутствует) ---
cat > /etc/nginx/sites-available/default <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    root /var/www/html;
    index index.html;
    server_name _;
    location / { try_files $uri $uri/ =404; }
}
EOF

systemctl enable nginx
systemctl start nginx

# --- SSH: уязвимая конфигурация ---
sed -i '/^PermitRootLogin/d'        /etc/ssh/sshd_config
sed -i '/^PasswordAuthentication/d' /etc/ssh/sshd_config
echo "PermitRootLogin yes"         >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >  /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

# --- Firewall: установлен, но намеренно деактивирован ---
ufw disable || true

echo "[node-app] provisioning done: LOW state configured"
