#!/bin/bash
# Общие шаги для всех target-узлов: demo-пользователь, sudoers, SSH password-auth.
# source'ится из node_*.sh (но удобнее inline'ить, чтобы не зависеть от cwd).
# Этот файл — справка; провижн-скрипты содержат свои копии.

set -e
export DEBIAN_FRONTEND=noninteractive

# --- Demo-пользователь ---
id -u demo &>/dev/null || useradd -m -s /bin/bash demo
echo "demo:demo" | chpasswd
usermod -aG sudo demo
echo 'demo ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/demo-nopasswd
chmod 440 /etc/sudoers.d/demo-nopasswd

# --- SSH password-auth (cloudimg по умолчанию запрещает) ---
sed -i '/^PermitRootLogin/d'        /etc/ssh/sshd_config
sed -i '/^PasswordAuthentication/d' /etc/ssh/sshd_config
echo "PermitRootLogin yes"         >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >  /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

# --- Базовые пакеты ---
apt-get update -qq
apt-get install -y -q ca-certificates curl gnupg lsb-release ufw

# --- Docker через официальный репозиторий ---
if ! command -v docker &>/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu jammy stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  usermod -aG docker demo
  systemctl enable docker
  systemctl start docker
fi
