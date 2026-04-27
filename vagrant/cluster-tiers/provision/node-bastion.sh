#!/bin/bash
# node-bastion (192.168.58.10)
# BASTION: только SSH-доступ, никаких web-сервисов
# Цель — jump host, минимальная атак-поверхность

set -e

# --- Demo-пользователь ---
id -u demo &>/dev/null || useradd -m -s /bin/bash demo
echo "demo:demo" | chpasswd
usermod -aG sudo demo
echo 'demo ALL=(ALL) NOPASSWD: /usr/sbin/ufw' > /etc/sudoers.d/demo-ufw
chmod 440 /etc/sudoers.d/demo-ufw

# --- Пакеты: ufw, без nginx (никаких веб-сервисов) ---
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -q ufw

# --- SSH: hardened (PermitRootLogin no, PasswordAuth yes для demo) ---
sed -i '/^PermitRootLogin/d'        /etc/ssh/sshd_config
sed -i '/^PasswordAuthentication/d' /etc/ssh/sshd_config
echo "PermitRootLogin no"          >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >  /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

# --- Firewall: только SSH разрешён, всё остальное блокировано ---
ufw --force enable
ufw allow ssh
ufw default deny incoming
ufw default allow outgoing

echo "[node-bastion] provisioned: BASTION — SSH only, hardened, ufw with deny-all default"
