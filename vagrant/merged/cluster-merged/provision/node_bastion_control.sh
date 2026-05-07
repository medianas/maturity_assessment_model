#!/bin/bash
# node-bastion-mg (192.168.59.5) — bastion + Ansible control-node для cluster-merged.
# Совмещённая роль: точка входа в кластер (SSH jump-host) + control-node для Ansible.
# Управляет: node-gitlab-pub / node-redmine-int / node-mattermost-int.

set -e
export DEBIAN_FRONTEND=noninteractive
SCENARIO="${SCENARIO:-broken}"
ROLE="${ROLE:-bastion}"

apt-get update -qq
apt-get install -y -q ansible sshpass python3-pip
pip3 install --quiet requests

# === Demo-пользователь для подключения paramiko из Python ===
id -u demo &>/dev/null || useradd -m -s /bin/bash -g vagrant demo
echo "demo:demo" | chpasswd
echo 'demo ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/demo-nopasswd
chmod 440 /etc/sudoers.d/demo-nopasswd
echo "PasswordAuthentication yes" > /etc/ssh/sshd_config.d/60-cloudimg-settings.conf
systemctl restart ssh

# === SSH-ключ для vagrant ===
sudo -u vagrant bash -e <<'INNER'
mkdir -p ~/.ssh && chmod 700 ~/.ssh
[ -f ~/.ssh/id_rsa ] || ssh-keygen -t rsa -b 2048 -N "" -f ~/.ssh/id_rsa -q
INNER

TARGETS=("192.168.59.10" "192.168.59.20" "192.168.59.30")
for ip in "${TARGETS[@]}"; do
  echo "Распространение SSH-ключа на $ip..."
  for i in {1..30}; do
    nc -z -w 2 "$ip" 22 2>/dev/null && break
    echo "  жду $ip:22 ($i/30)..."
    sleep 3
  done
  sudo -u vagrant sshpass -p demo ssh-copy-id \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "demo@$ip" 2>&1 | tail -3 || echo "WARN: ssh-copy-id $ip failed"
done

# === Inventory: одновременно отражает service-группы (для devsecops-плейбуков)
#     и role-группы (для будущих платформенных плейбуков) ===
mkdir -p /etc/ansible
cat > /etc/ansible/hosts <<'EOF'
[gitlab_hosts]
node-gitlab-pub ansible_host=192.168.59.10

[redmine_hosts]
node-redmine-int ansible_host=192.168.59.20

[mattermost_hosts]
node-mattermost-int ansible_host=192.168.59.30

[public_role]
node-gitlab-pub

[internal_role]
node-redmine-int
node-mattermost-int

[bastion_role]
node-bastion-mg ansible_host=192.168.59.5

[targets:children]
gitlab_hosts
redmine_hosts
mattermost_hosts

[targets:vars]
ansible_user=demo
ansible_ssh_private_key_file=/home/vagrant/.ssh/id_rsa
ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
ansible_become=true
ansible_become_method=sudo
ansible_python_interpreter=/usr/bin/python3
EOF

# === Плейбуки ===
mkdir -p /opt/playbooks
if [ -d /tmp/playbooks ]; then
  cp -r /tmp/playbooks/. /opt/playbooks/
  chown -R vagrant:vagrant /opt/playbooks
  echo "Плейбуки скопированы ($(find /opt/playbooks -name '*.yml' | wc -l) yml-файлов)"
fi

cat > /etc/ansible/ansible.cfg <<'EOF'
[defaults]
inventory = /etc/ansible/hosts
host_key_checking = False
stdout_callback = default
deprecation_warnings = False
retry_files_enabled = False
EOF

# === ufw для bastion (только SSH открыт наружу) ===
apt-get install -y -q ufw
ufw --force enable
ufw allow ssh

# === Маркеры: scenario + role ===
mkdir -p /etc/devsec
echo "scenario=$SCENARIO" > /etc/devsec/state.conf
echo "service=control"   >> /etc/devsec/state.conf

echo "role=$ROLE" > /etc/devsec/role.conf

echo ""
echo "=== Ansible connectivity test ==="
sudo -u vagrant ansible targets -m ping || echo "WARN: ansible ping failed"

echo ""
echo "[node-bastion-mg] provisioning done — cluster-merged scenario=$SCENARIO role=$ROLE"
