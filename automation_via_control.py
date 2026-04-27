"""
Запуск Ansible-плейбуков на target-узлах через выделенную control-node.

Архитектура:
    Host (Windows) ──SSH──> control-node (Linux+ansible) ──SSH──> target-узлы

В отличие от обычного AnsibleAutomationManager, который пытается запустить
ansible-playbook локально (через subprocess.run), этот менеджер:

  1. Подключается по SSH из Python (paramiko) к control-node.
  2. Запускает там команду: ansible-playbook /opt/playbooks/<path> --limit <target>
  3. Парсит returncode + stdout/stderr.
  4. Возвращает AutomationExecutionResult.

Это решает проблему запуска Ansible с Windows-host.
"""

from typing import Optional
import time

import paramiko

from automation import AnsibleAutomationManager
from models import (
    CorrectionAction,
    TargetNode,
    AutomationExecutionResult,
)


class ControlNodeAutomationManager(AnsibleAutomationManager):
    """Менеджер автоматизации, выполняющий плейбуки на control-node."""

    def __init__(
        self,
        control_host: str,
        control_user: str = "demo",
        control_password: str = "demo",
        playbooks_root: str = "/opt/playbooks",
        ansible_user: str = "vagrant",
        ansible_inventory: str = "/etc/ansible/hosts",
        ansible_inventory_path: Optional[str] = None,
    ):
        super().__init__(ansible_inventory_path=ansible_inventory_path)
        self.control_host = control_host
        self.control_user = control_user
        self.control_password = control_password
        self.playbooks_root = playbooks_root
        self.ansible_user = ansible_user
        self.ansible_inventory = ansible_inventory

    # --- Маппинг IP→alias в /etc/ansible/hosts (все 3 кластера) ---
    HOST_MAP = {
        # cluster-base
        "192.168.56.10": "node-critical",
        "192.168.56.20": "node-app",
        "192.168.56.30": "node-secure",
        # cluster-lifecycle
        "192.168.57.10": "node-dev",
        "192.168.57.20": "node-staging",
        "192.168.57.30": "node-prod",
        # cluster-tiers
        "192.168.58.10": "node-bastion",
        "192.168.58.20": "node-internal",
        "192.168.58.30": "node-public",
    }

    def _resolve_host_alias(self, ip: str) -> str:
        """IP → alias из inventory; если неизвестен — возвращает сам IP."""
        return self.HOST_MAP.get(ip, ip)

    def _run_playbook(
        self,
        playbook_path: str,
        target_host: str,
        extra_vars: dict = None,
    ) -> AutomationExecutionResult:
        """Запускает плейбук на target_host через control-node.

        playbook_path может быть как абсолютным путём в host-проекте
        (например 'playbooks/security/enable_https.yml'), так и просто
        относительным от playbooks-root. Мы извлекаем последние две части
        пути и собираем итоговый remote-путь как
        {playbooks_root}/<category>/<name>.yml.
        """
        start_time = time.time()
        target_alias = self._resolve_host_alias(target_host)

        # Извлекаем 'security/enable_https.yml' из любого варианта пути
        rel = playbook_path.replace("\\", "/")
        if "playbooks/" in rel:
            rel = rel.split("playbooks/", 1)[1]
        remote_playbook = f"{self.playbooks_root.rstrip('/')}/{rel}"

        # Собираем команду
        cmd_parts = [
            "sudo", "-u", self.ansible_user,
            "ansible-playbook",
            "-i", self.ansible_inventory,
            remote_playbook,
            "--limit", target_alias,
        ]
        if extra_vars:
            for key, value in extra_vars.items():
                cmd_parts += ["--extra-vars", f"{key}={value}"]
        cmd = " ".join(cmd_parts)

        print(f"        [control] {self.control_host} → {target_alias}: {rel}")

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                self.control_host,
                username=self.control_user,
                password=self.control_password,
                timeout=15,
                allow_agent=False,
                look_for_keys=False,
            )
            stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
            rc = stdout.channel.recv_exit_status()
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
            client.close()
        except Exception as exc:
            return AutomationExecutionResult(
                action_id=playbook_path,
                success=False,
                execution_time=time.time() - start_time,
                stdout="",
                stderr=f"SSH к control-node {self.control_host} не удался: {exc}",
                idempotent=False,
            )

        execution_time = time.time() - start_time
        success = rc == 0

        return AutomationExecutionResult(
            action_id=playbook_path,
            success=success,
            execution_time=execution_time,
            stdout=out,
            stderr=err,
            idempotent=success,
        )
