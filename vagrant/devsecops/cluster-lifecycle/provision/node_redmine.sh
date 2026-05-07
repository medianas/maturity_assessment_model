#!/bin/bash
# node-redmine (192.168.56.20) — Redmine + PostgreSQL через Docker.

set -e
export DEBIAN_FRONTEND=noninteractive
SCENARIO="${SCENARIO:-broken}"
echo "[node-redmine] scenario=$SCENARIO"

# === Common ===
id -u demo &>/dev/null || useradd -m -s /bin/bash demo
echo "demo:demo" | chpasswd
usermod -aG sudo demo
echo 'demo ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/demo-nopasswd
chmod 440 /etc/sudoers.d/demo-nopasswd

sed -i '/^PermitRootLogin/d'        /etc/ssh/sshd_config
sed -i '/^PasswordAuthentication/d' /etc/ssh/sshd_config
echo "PermitRootLogin yes"         >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >  /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

apt-get update -qq
apt-get install -y -q ca-certificates curl gnupg lsb-release ufw

mkdir -p /etc/devsec
if [ -n "$ROLE" ]; then
  echo "role=$ROLE" > /etc/devsec/role.conf
  echo "[node-redmine] role=$ROLE marker записан в /etc/devsec/role.conf"
fi

if [ "$SCENARIO" = "missing" ]; then
  ufw --force enable
  ufw allow ssh
  echo "scenario=missing" > /etc/devsec/state.conf
  echo "service=redmine" >> /etc/devsec/state.conf
  echo "[node-redmine] scenario=missing: Redmine НЕ установлен"
  exit 0
fi

# === Docker ===
if ! command -v docker &>/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu jammy stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
  usermod -aG docker demo
  systemctl enable docker --now
fi

# === Redmine + Postgres ===
mkdir -p /opt/redmine
cd /opt/redmine

cat > /opt/redmine/docker-compose.yml <<'EOF'
services:
  redmine-db:
    image: postgres:15
    container_name: redmine-db
    restart: always
    environment:
      POSTGRES_DB: redmine
      POSTGRES_USER: redmine
      POSTGRES_PASSWORD: redminepass
    volumes:
      - /opt/redmine/db:/var/lib/postgresql/data

  redmine:
    image: redmine:5.1
    container_name: redmine
    restart: always
    depends_on:
      - redmine-db
    environment:
      REDMINE_DB_POSTGRES: redmine-db
      REDMINE_DB_DATABASE: redmine
      REDMINE_DB_USERNAME: redmine
      REDMINE_DB_PASSWORD: redminepass
      REDMINE_SECRET_KEY_BASE: insecure-demo-key-change-me
    ports:
      - "3000:3000"
    volumes:
      - /opt/redmine/files:/usr/src/redmine/files
EOF

# nginx-frontend для HTTPS на порту 443 (только для ok)
if [ "$SCENARIO" = "ok" ]; then
  apt-get install -y -q nginx openssl
  NODE_IP=$(ip -4 -o addr show | awk '/192\.168\.5[6789]\./ {print $4}' | cut -d/ -f1 | head -n1)
  mkdir -p /etc/nginx/ssl
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/server.key \
    -out    /etc/nginx/ssl/server.crt \
    -subj   "/C=RU/ST=Moscow/L=Moscow/O=Demo/CN=${NODE_IP}" \
    2>/dev/null

  cat > /etc/nginx/sites-available/default <<'EOF'
server {
    listen 80 default_server;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl default_server;
    ssl_certificate     /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }
}
EOF
  systemctl enable nginx
  systemctl restart nginx
  HTTPS_ENABLED="true"
else
  HTTPS_ENABLED="false"
fi

ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3000/tcp

cd /opt/redmine && docker compose up -d

echo "[node-redmine] waiting for Redmine..."
for i in {1..30}; do
  if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:3000/" | grep -qE "200|302"; then
    echo "[node-redmine] Redmine up ($i*10s)"
    break
  fi
  printf "."
  sleep 10
done
echo ""

mkdir -p /etc/devsec
echo "scenario=$SCENARIO" > /etc/devsec/state.conf
echo "service=redmine"   >> /etc/devsec/state.conf
echo "https=$HTTPS_ENABLED" >> /etc/devsec/state.conf

if [ -n "$ROLE" ]; then
  echo "role=$ROLE" > /etc/devsec/role.conf
  echo "[node-redmine] role=$ROLE marker записан в /etc/devsec/role.conf"
fi

echo "[node-redmine] done: scenario=$SCENARIO https=$HTTPS_ENABLED role=${ROLE:-none}"
