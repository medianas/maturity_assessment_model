#!/bin/bash
# node-mattermost (192.168.56.30) — Mattermost + PostgreSQL через Docker.

set -e
export DEBIAN_FRONTEND=noninteractive
SCENARIO="${SCENARIO:-broken}"
echo "[node-mattermost] scenario=$SCENARIO"

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
  echo "[node-mattermost] role=$ROLE marker записан в /etc/devsec/role.conf"
fi

if [ "$SCENARIO" = "missing" ]; then
  ufw --force enable
  ufw allow ssh
  echo "scenario=missing" > /etc/devsec/state.conf
  echo "service=mattermost" >> /etc/devsec/state.conf
  echo "[node-mattermost] scenario=missing: Mattermost НЕ установлен"
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

# === Mattermost + Postgres ===
mkdir -p /opt/mattermost/{config,data,logs,plugins,client-plugins}
chown -R 2000:2000 /opt/mattermost
cd /opt/mattermost

cat > /opt/mattermost/docker-compose.yml <<'EOF'
services:
  mm-db:
    image: postgres:15
    container_name: mm-db
    restart: always
    environment:
      POSTGRES_DB: mattermost
      POSTGRES_USER: mmuser
      POSTGRES_PASSWORD: mmpass
    volumes:
      - /opt/mattermost/db:/var/lib/postgresql/data

  mattermost:
    image: mattermost/mattermost-team-edition:9.5
    container_name: mattermost
    restart: always
    depends_on:
      - mm-db
    environment:
      MM_SQLSETTINGS_DRIVERNAME: postgres
      MM_SQLSETTINGS_DATASOURCE: "postgres://mmuser:mmpass@mm-db:5432/mattermost?sslmode=disable&connect_timeout=10"
      MM_SERVICESETTINGS_SITEURL: ""
    ports:
      - "8065:8065"
    volumes:
      - /opt/mattermost/config:/mattermost/config
      - /opt/mattermost/data:/mattermost/data
      - /opt/mattermost/logs:/mattermost/logs
      - /opt/mattermost/plugins:/mattermost/plugins
      - /opt/mattermost/client-plugins:/mattermost/client/plugins
EOF

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
        proxy_pass http://127.0.0.1:8065;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
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
ufw allow 8065/tcp

cd /opt/mattermost && docker compose up -d

echo "[node-mattermost] waiting for Mattermost..."
for i in {1..30}; do
  if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8065/api/v4/system/ping" | grep -q "200"; then
    echo "[node-mattermost] Mattermost up ($i*10s)"
    break
  fi
  printf "."
  sleep 10
done
echo ""

mkdir -p /etc/devsec
echo "scenario=$SCENARIO" > /etc/devsec/state.conf
echo "service=mattermost" >> /etc/devsec/state.conf
echo "https=$HTTPS_ENABLED" >> /etc/devsec/state.conf

if [ -n "$ROLE" ]; then
  echo "role=$ROLE" > /etc/devsec/role.conf
  echo "[node-mattermost] role=$ROLE marker записан в /etc/devsec/role.conf"
fi

echo "[node-mattermost] done: scenario=$SCENARIO https=$HTTPS_ENABLED role=${ROLE:-none}"
