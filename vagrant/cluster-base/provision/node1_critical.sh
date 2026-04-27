#!/bin/bash
# node-critical (192.168.56.10)
# Начальный уровень зрелости: CRITICAL
# Нарушения: нет веб-сервисов, слабый SSH, нет firewall

set -e

# --- Пользователь для аудита ---
id -u demo &>/dev/null || useradd -m -s /bin/bash demo
echo "demo:demo" | chpasswd
usermod -aG sudo demo
# NOPASSWD: ALL — нужно audit (без TTY) и для Ansible с control-node
echo 'demo ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/demo-nopasswd
chmod 440 /etc/sudoers.d/demo-nopasswd

# --- SSH: максимально уязвимая конфигурация ---
sed -i '/^PermitRootLogin/d'        /etc/ssh/sshd_config
sed -i '/^PasswordAuthentication/d' /etc/ssh/sshd_config
echo "PermitRootLogin yes"         >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes"  >> /etc/ssh/sshd_config
# Переопределяем cloud-init настройки (jammy64 запрещает пароли через sshd_config.d)
echo "PasswordAuthentication yes"  >  /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

# --- Firewall: отсутствует (не устанавливаем) ---
# ufw намеренно не устанавливается

# --- Веб-сервисы: не устанавливаем ---
# Порты 80 и 443 закрыты — сервисов нет

echo "[node-critical] provisioning done: CRITICAL state configured"
