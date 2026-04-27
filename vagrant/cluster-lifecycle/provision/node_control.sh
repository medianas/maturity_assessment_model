#!/bin/bash
# node-control (192.168.57.5) — Ansible control-node для cluster-lifecycle.
# Управляет node-dev / node-staging / node-prod.

set -e

export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -q ansible sshpass

# Demo-пользователь для подключения paramiko из Python к control
id -u demo &>/dev/null || useradd -m -s /bin/bash -g vagrant demo
echo "demo:demo" | chpasswd
echo 'demo ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/demo-nopasswd
chmod 440 /etc/sudoers.d/demo-nopasswd
echo "PasswordAuthentication yes" > /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

sudo -u vagrant bash -e <<'INNER'
mkdir -p ~/.ssh && chmod 700 ~/.ssh
[ -f ~/.ssh/id_rsa ] || ssh-keygen -t rsa -b 2048 -N "" -f ~/.ssh/id_rsa -q
INNER

TARGETS=("192.168.57.10" "192.168.57.20" "192.168.57.30")
for ip in "${TARGETS[@]}"; do
  echo "Распространение SSH-ключа на $ip..."
  for i in {1..15}; do
    nc -z -w 2 "$ip" 22 2>/dev/null && break
    echo "  жду $ip:22 ($i/15)..."
    sleep 2
  done
  sudo -u vagrant sshpass -p demo ssh-copy-id \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "demo@$ip" 2>&1 | tail -3 || echo "WARN: ssh-copy-id $ip failed"
done

mkdir -p /etc/ansible
cat > /etc/ansible/hosts <<'EOF'
[targets]
node-dev     ansible_host=192.168.57.10
node-staging ansible_host=192.168.57.20
node-prod    ansible_host=192.168.57.30

[targets:vars]
ansible_user=demo
ansible_ssh_private_key_file=/home/vagrant/.ssh/id_rsa
ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
ansible_become=true
ansible_become_method=sudo
ansible_python_interpreter=/usr/bin/python3
EOF

mkdir -p /opt/playbooks
if [ -d /tmp/playbooks ]; then
  cp -r /tmp/playbooks/. /opt/playbooks/
  chown -R vagrant:vagrant /opt/playbooks
  echo "Плейбуки скопированы в /opt/playbooks ($(find /opt/playbooks -name '*.yml' | wc -l) yml-файлов)"
fi

cat > /etc/ansible/ansible.cfg <<'EOF'
[defaults]
inventory = /etc/ansible/hosts
host_key_checking = False
stdout_callback = default
deprecation_warnings = False
retry_files_enabled = False
EOF

echo ""
echo "=== Ansible connectivity test ==="
sudo -u vagrant ansible targets -m ping || echo "WARN: ansible ping failed"

echo ""
echo "[node-control] provisioning done (cluster-lifecycle)"
