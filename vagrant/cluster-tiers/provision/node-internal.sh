#!/bin/bash
# node-internal (192.168.58.20)
# INTERNAL: внутренний сервис, HTTP only (внутри сети — допустимо), ufw активен
# Цель — внутреннее приложение, не выходящее за периметр

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
apt-get install -y -q nginx ufw

# --- Nginx: HTTP only (внутренний сервис, без HTTPS) ---
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

# --- SSH: PermitRootLogin no, PasswordAuth yes (полу-настроен) ---
sed -i '/^PermitRootLogin/d'        /etc/ssh/sshd_config
sed -i '/^PasswordAuthentication/d' /etc/ssh/sshd_config
echo "PermitRootLogin no"          >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >  /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

# --- Firewall: SSH + HTTP разрешены, остальное блокировано ---
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw default deny incoming
ufw default allow outgoing

echo "[node-internal] provisioned: INTERNAL — HTTP only, semi-hardened SSH, ufw active"
