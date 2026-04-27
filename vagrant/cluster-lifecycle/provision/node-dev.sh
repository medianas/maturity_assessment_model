#!/bin/bash
# node-dev (192.168.57.10)
# DEV: HTTP only, weak SSH, no firewall
# Цель — показать "сырое" окружение разработки (минимум защиты)

set -e

# --- Demo-пользователь для аудита ---
id -u demo &>/dev/null || useradd -m -s /bin/bash demo
echo "demo:demo" | chpasswd
usermod -aG sudo demo
echo 'demo ALL=(ALL) NOPASSWD: /usr/sbin/ufw' > /etc/sudoers.d/demo-ufw
chmod 440 /etc/sudoers.d/demo-ufw

# --- Пакеты ---
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -q nginx

# --- Nginx: только HTTP ---
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

# --- SSH: уязвимая конфигурация (root yes, password yes) ---
sed -i '/^PermitRootLogin/d'        /etc/ssh/sshd_config
sed -i '/^PasswordAuthentication/d' /etc/ssh/sshd_config
echo "PermitRootLogin yes"         >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >  /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

# --- Firewall: ufw отключён (правила выключены) ---
ufw disable 2>/dev/null || true

echo "[node-dev] provisioned: DEV state — HTTP only, weak SSH, ufw disabled"
