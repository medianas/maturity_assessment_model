from datetime import datetime
from typing import List
import socket
import paramiko
from models import TargetNode, AuditReport, AuditCheckResult, ServiceStatus
from config import AUDIT_PROFILES


class InfrastructureAudit:

    def __init__(self):
        self._check_registry = [
            "service_availability", "https_enabled", "ssh_config",
            "firewall_status", "connectivity",
            "gitlab_integration", "redmine_integration", "mattermost_integration"
        ]

    def audit_node_configuration(self, node: TargetNode, profile: str) -> AuditReport:
        results = []
        profile_config = AUDIT_PROFILES.get(profile, AUDIT_PROFILES["default"])
        checks = profile_config.get("checks", [])

        for check_name in checks:
            result = self._run_check(node, check_name)
            results.append(result)

        return AuditReport(
            node_ip=node.ip_address,
            checks=results,
            timestamp=datetime.now().isoformat()
        )

    def _run_check(self, node: TargetNode, check_name: str) -> AuditCheckResult:
        check_methods = {
            "service_availability": self._check_service_availability,
            "https_enabled": self._check_https_enabled,
            "ssh_config": self._check_ssh_config,
            "firewall_status": self._check_firewall,
            "connectivity": self._check_connectivity,
            "gitlab_integration": self._check_gitlab_integration,
            "redmine_integration": self._check_redmine_integration,
            "mattermost_integration": self._check_mattermost_integration
        }
        method = check_methods.get(check_name, self._check_unknown)
        return method(node)

    def _check_port_open(self, host: str, port: int, timeout: float = 5.0) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _check_service_availability(self, node: TargetNode) -> AuditCheckResult:
        services_to_check = [("HTTP", 80), ("HTTPS", 443), ("SSH", 22)]
        available = []
        for name, port in services_to_check:
            if self._check_port_open(node.ip_address, port):
                available.append(f"{name}({port})")

        compliant = len(available) > 0
        return AuditCheckResult(
            check_name="service_availability",
            status=ServiceStatus.RUNNING if compliant else ServiceStatus.STOPPED,
            compliant=compliant,
            actual_value=", ".join(available) if available else "none",
            expected_value="HTTP/HTTPS/SSH available",
            details=f"Доступные сервисы: {', '.join(available)}" if available else "Сервисы недоступны"
        )

    def _check_https_enabled(self, node: TargetNode) -> AuditCheckResult:
        https_available = self._check_port_open(node.ip_address, 443)
        http_available = self._check_port_open(node.ip_address, 80)

        if https_available:
            compliant, actual_value, details = True, "HTTPS enabled", "HTTPS доступен"
        elif http_available:
            compliant, actual_value, details = False, "HTTP only", "Только HTTP доступен, HTTPS отсутствует"
        else:
            compliant, actual_value, details = False, "No web service", "Веб-сервисы недоступны"

        return AuditCheckResult(
            check_name="https_enabled",
            status=ServiceStatus.RUNNING if https_available or http_available else ServiceStatus.STOPPED,
            compliant=compliant,
            actual_value=actual_value,
            expected_value="HTTPS enabled",
            details=details
        )

    def _check_ssh_config(self, node: TargetNode) -> AuditCheckResult:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                node.ip_address,
                username=node.ssh_credentials.username,
                password=node.ssh_credentials.password,
                key_filename=node.ssh_credentials.private_key_path,
                timeout=10
            )
            _, stdout, _ = ssh.exec_command(
                "grep -E 'PermitRootLogin|PasswordAuthentication' /etc/ssh/sshd_config"
            )
            config_output = stdout.read().decode().strip()
            ssh.close()

            permit_root = "PermitRootLogin no" in config_output
            password_auth = "PasswordAuthentication no" in config_output
            compliant = permit_root and password_auth
            actual_value = f"RootLogin:{'no' if permit_root else 'yes'}, PasswordAuth:{'no' if password_auth else 'yes'}"

            return AuditCheckResult(
                check_name="ssh_config",
                status=ServiceStatus.RUNNING,
                compliant=compliant,
                actual_value=actual_value,
                expected_value="PermitRootLogin=no, PasswordAuthentication=no",
                details=f"SSH конфигурация: {actual_value}"
            )
        except Exception as e:
            return AuditCheckResult(
                check_name="ssh_config",
                status=ServiceStatus.ERROR,
                compliant=False,
                actual_value="SSH connection failed",
                expected_value="SSH accessible with proper config",
                details=f"Ошибка подключения SSH: {str(e)}"
            )

    def _check_firewall(self, node: TargetNode) -> AuditCheckResult:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                node.ip_address,
                username=node.ssh_credentials.username,
                password=node.ssh_credentials.password,
                key_filename=node.ssh_credentials.private_key_path,
                timeout=10
            )
            # Проверяем реальный статус правил, а не только systemd-юнит.
            # ufw как oneshot может быть "active" в systemd, но правила выключены.
            _, stdout, _ = ssh.exec_command(
                "if command -v ufw >/dev/null 2>&1; then "
                "  sudo ufw status | head -1 | awk '{print tolower($2)}'; "
                "elif command -v firewall-cmd >/dev/null 2>&1; then "
                "  firewall-cmd --state 2>/dev/null || echo inactive; "
                "else echo no_firewall; fi"
            )
            firewall_status = stdout.read().decode().strip().lower()
            ssh.close()

            if firewall_status in ['active', 'running']:
                compliant, actual_value, details = True, "active", "Firewall активен и правила загружены"
            elif firewall_status == 'no_firewall':
                compliant, actual_value, details = False, "not_installed", "Firewall не установлен"
            else:
                compliant, actual_value, details = False, "inactive", "Firewall установлен но правила выключены"

            return AuditCheckResult(
                check_name="firewall_status",
                status=ServiceStatus.RUNNING,
                compliant=compliant,
                actual_value=actual_value,
                expected_value="active",
                details=details
            )
        except Exception as e:
            return AuditCheckResult(
                check_name="firewall_status",
                status=ServiceStatus.ERROR,
                compliant=False,
                actual_value="check_failed",
                expected_value="active",
                details=f"Ошибка проверки firewall: {str(e)}"
            )

    def _check_connectivity(self, node: TargetNode) -> AuditCheckResult:
        reachable = self._check_port_open(node.ip_address, 22, 10.0)
        return AuditCheckResult(
            check_name="connectivity",
            status=ServiceStatus.RUNNING if reachable else ServiceStatus.STOPPED,
            compliant=reachable,
            actual_value="reachable" if reachable else "unreachable",
            expected_value="reachable",
            details="Узел доступен по сети" if reachable else "Узел недоступен по сети"
        )

    def _check_unknown(self, node: TargetNode) -> AuditCheckResult:
        return AuditCheckResult(
            check_name="unknown",
            status=ServiceStatus.UNKNOWN,
            compliant=False,
            actual_value="unknown",
            expected_value="known",
            details="Неизвестный тип проверки"
        )

    def _check_gitlab_integration(self, node: TargetNode) -> AuditCheckResult:
        try:
            gitlab_available = any(
                self._check_port_open(node.ip_address, p) for p in [80, 443, 8080]
            )
            if gitlab_available:
                https_available = self._check_port_open(node.ip_address, 443)
                compliant = https_available
                actual_value = "available_with_https" if https_available else "available_http_only"
                details = "GitLab доступен" + (" с HTTPS" if https_available else ", но без HTTPS")
            else:
                compliant, actual_value = False, "not_available"
                details = "GitLab недоступен на стандартных портах"

            return AuditCheckResult(
                check_name="gitlab_integration",
                status=ServiceStatus.RUNNING if gitlab_available else ServiceStatus.STOPPED,
                compliant=compliant,
                actual_value=actual_value,
                expected_value="available_with_https",
                details=details
            )
        except Exception as e:
            return AuditCheckResult(
                check_name="gitlab_integration",
                status=ServiceStatus.ERROR,
                compliant=False,
                actual_value="check_failed",
                expected_value="available_with_https",
                details=f"Ошибка проверки GitLab: {str(e)}"
            )

    def _check_redmine_integration(self, node: TargetNode) -> AuditCheckResult:
        try:
            redmine_available = any(
                self._check_port_open(node.ip_address, p) for p in [80, 443, 3000]
            )
            if redmine_available:
                https_available = self._check_port_open(node.ip_address, 443)
                compliant = https_available
                actual_value = "available_with_https" if https_available else "available_http_only"
                details = "Redmine доступен" + (" с HTTPS" if https_available else ", но без HTTPS")
            else:
                compliant, actual_value = False, "not_available"
                details = "Redmine недоступен на стандартных портах"

            return AuditCheckResult(
                check_name="redmine_integration",
                status=ServiceStatus.RUNNING if redmine_available else ServiceStatus.STOPPED,
                compliant=compliant,
                actual_value=actual_value,
                expected_value="available_with_https",
                details=details
            )
        except Exception as e:
            return AuditCheckResult(
                check_name="redmine_integration",
                status=ServiceStatus.ERROR,
                compliant=False,
                actual_value="check_failed",
                expected_value="available_with_https",
                details=f"Ошибка проверки Redmine: {str(e)}"
            )

    def _check_mattermost_integration(self, node: TargetNode) -> AuditCheckResult:
        try:
            mm_available = any(
                self._check_port_open(node.ip_address, p) for p in [80, 443, 8065]
            )
            if mm_available:
                https_available = self._check_port_open(node.ip_address, 443)
                compliant = https_available
                actual_value = "available_with_https" if https_available else "available_http_only"
                details = "Mattermost доступен" + (" с HTTPS" if https_available else ", но без HTTPS")
            else:
                compliant, actual_value = False, "not_available"
                details = "Mattermost недоступен на стандартных портах"

            return AuditCheckResult(
                check_name="mattermost_integration",
                status=ServiceStatus.RUNNING if mm_available else ServiceStatus.STOPPED,
                compliant=compliant,
                actual_value=actual_value,
                expected_value="available_with_https",
                details=details
            )
        except Exception as e:
            return AuditCheckResult(
                check_name="mattermost_integration",
                status=ServiceStatus.ERROR,
                compliant=False,
                actual_value="check_failed",
                expected_value="available_with_https",
                details=f"Ошибка проверки Mattermost: {str(e)}"
            )
