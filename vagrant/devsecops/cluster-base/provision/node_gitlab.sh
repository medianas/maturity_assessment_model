#!/bin/bash
# node-gitlab (192.168.56.10) — GitLab CE через Docker.
# Сценарии:
#   missing — НИЧЕГО не ставится, кроме OS+SSH+ufw
#   broken  — GitLab установлен, но HTTP only (без HTTPS), webhook-token простой
#   ok      — GitLab установлен с HTTPS (self-signed), seed-токен для интеграций

set -e
export DEBIAN_FRONTEND=noninteractive
SCENARIO="${SCENARIO:-broken}"
echo "[node-gitlab] scenario=$SCENARIO"

# === Common: demo-пользователь, SSH-password-auth ===
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

# === Маркер сетевой роли (если задан в env, нужен и для missing-сценария) ===
mkdir -p /etc/devsec
if [ -n "$ROLE" ]; then
  echo "role=$ROLE" > /etc/devsec/role.conf
  echo "[node-gitlab] role=$ROLE marker записан в /etc/devsec/role.conf"
fi

# === Сценарий missing — на этом и заканчиваем ===
if [ "$SCENARIO" = "missing" ]; then
  ufw --force enable
  ufw allow ssh
  echo "scenario=missing" > /etc/devsec/state.conf
  echo "service=gitlab"  >> /etc/devsec/state.conf
  echo "[node-gitlab] scenario=missing: GitLab НЕ установлен (только SSH+ufw)"
  exit 0
fi

# === Установка Docker (для broken и ok) ===
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

# === GitLab через docker-compose ===
mkdir -p /opt/gitlab/{config,logs,data}
cd /opt/gitlab

# Определяем IP private network (eth1)
NODE_IP=$(ip -4 -o addr show | awk '/192\.168\.5[6789]\./ {print $4}' | cut -d/ -f1 | head -n1)
echo "[node-gitlab] detected NODE_IP=$NODE_IP"

if [ "$SCENARIO" = "ok" ]; then
  GITLAB_URL="https://${NODE_IP}"
  HTTPS_ENABLED="true"
else
  # broken — только HTTP
  GITLAB_URL="http://${NODE_IP}"
  HTTPS_ENABLED="false"
fi

# Self-signed cert для ok-сценария
if [ "$SCENARIO" = "ok" ]; then
  mkdir -p /opt/gitlab/config/ssl
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /opt/gitlab/config/ssl/${NODE_IP}.key \
    -out    /opt/gitlab/config/ssl/${NODE_IP}.crt \
    -subj   "/C=RU/ST=Moscow/L=Moscow/O=Demo/CN=${NODE_IP}" \
    2>/dev/null
fi

cat > /opt/gitlab/docker-compose.yml <<EOF
services:
  gitlab:
    image: gitlab/gitlab-ce:16.11.10-ce.0
    container_name: gitlab
    restart: always
    hostname: '${NODE_IP}'
    environment:
      GITLAB_OMNIBUS_CONFIG: |
        external_url '${GITLAB_URL}'
        gitlab_rails['initial_root_password'] = 'demoDEMOdemo123!'
        gitlab_rails['gitlab_shell_ssh_port'] = 2222
        prometheus_monitoring['enable'] = false
        nginx['enable'] = true
EOF

if [ "$HTTPS_ENABLED" = "true" ]; then
  cat >> /opt/gitlab/docker-compose.yml <<EOF
        nginx['ssl_certificate']     = "/etc/gitlab/ssl/${NODE_IP}.crt"
        nginx['ssl_certificate_key'] = "/etc/gitlab/ssl/${NODE_IP}.key"
        nginx['redirect_http_to_https'] = true
EOF
fi

cat >> /opt/gitlab/docker-compose.yml <<EOF
    ports:
      - "80:80"
      - "443:443"
      - "2222:22"
    volumes:
      - /opt/gitlab/config:/etc/gitlab
      - /opt/gitlab/logs:/var/log/gitlab
      - /opt/gitlab/data:/var/opt/gitlab
    shm_size: '256m'
EOF

# === ufw ===
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 2222/tcp

# === Запуск ===
echo "[node-gitlab] starting GitLab container (это займёт 5-10 минут на первом старте)..."
cd /opt/gitlab && docker compose up -d

# Ждём пока GitLab станет здоровым (max 8 минут)
echo "[node-gitlab] waiting for GitLab health..."
for i in {1..48}; do
  if curl -sk -o /dev/null -w "%{http_code}" "${GITLAB_URL}/users/sign_in" | grep -qE "200|302"; then
    echo "[node-gitlab] GitLab is up! ($i*10s)"
    break
  fi
  printf "."
  sleep 10
done
echo ""

# === Маркер: scenario состояния + сетевая роль (если задана) ===
mkdir -p /etc/devsec
echo "scenario=$SCENARIO" > /etc/devsec/state.conf
echo "service=gitlab"    >> /etc/devsec/state.conf
echo "https=$HTTPS_ENABLED" >> /etc/devsec/state.conf

# Сетевая роль из ENV (для merged-стенда: public/internal/bastion).
# Не задана — обычный devsecops-стенд, маркер не пишется.
if [ -n "$ROLE" ]; then
  echo "role=$ROLE" > /etc/devsec/role.conf
  echo "[node-gitlab] role=$ROLE marker записан в /etc/devsec/role.conf"
fi

echo "[node-gitlab] provisioning done: scenario=$SCENARIO, https=$HTTPS_ENABLED, role=${ROLE:-none}"
