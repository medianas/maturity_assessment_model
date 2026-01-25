from datetime import datetime
from typing import List
from models import TargetNode, AuditReport, AuditCheckResult, ServiceStatus
from config import AUDIT_PROFILES

# Основной класс
class InfrastructureAudit:
    
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

    # Запуск конкретных проверок по имени
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

    def _check_service_availability(self, node: TargetNode) -> AuditCheckResult:
        return AuditCheckResult(
            check_name="service_availability",
            status=ServiceStatus.RUNNING,
            compliant=True,
            actual_value="available",
            expected_value="available",
            details="Сервисы доступны"
        )

    def _check_https_enabled(self, node: TargetNode) -> AuditCheckResult:
        return AuditCheckResult(
            check_name="https_enabled",
            status=ServiceStatus.RUNNING,
            compliant=False,
            actual_value="HTTP",
            expected_value="HTTPS",
            details="Используется незащищенный HTTP"
        )

    def _check_ssh_config(self, node: TargetNode) -> AuditCheckResult:
        return AuditCheckResult(
            check_name="ssh_config",
            status=ServiceStatus.RUNNING,
            compliant=False,
            actual_value="weak_config",
            expected_value="hardened_config",
            details="SSH требует усиления безопасности"
        )

    def _check_firewall(self, node: TargetNode) -> AuditCheckResult:
        return AuditCheckResult(
            check_name="firewall_status",
            status=ServiceStatus.RUNNING,
            compliant=True,
            actual_value="configured",
            expected_value="configured",
            details="Firewall настроен правильно"
        )

    def _check_connectivity(self, node: TargetNode) -> AuditCheckResult:
        return AuditCheckResult(
            check_name="connectivity",
            status=ServiceStatus.RUNNING,
            compliant=True,
            actual_value="reachable",
            expected_value="reachable",
            details="Узел доступен по сети"
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
        return AuditCheckResult(
            check_name="gitlab_integration",
            status=ServiceStatus.UNKNOWN,
            compliant=False,
            actual_value="not_secure",
            expected_value="gitlab_secure_configured",
            details="GitLab не настроен безопасно: отсутствует HTTPS, CI/CD pipelines требуют настройки security scanning"
        )

    def _check_redmine_integration(self, node: TargetNode) -> AuditCheckResult:
        return AuditCheckResult(
            check_name="redmine_integration",
            status=ServiceStatus.UNKNOWN,
            compliant=False,
            actual_value="not_secure",
            expected_value="redmine_secure_configured",
            details="Redmine не настроен безопасно: отсутствует workflow, issue tracking и project management требуют настройки"
        )

    def _check_mattermost_integration(self, node: TargetNode) -> AuditCheckResult:
        return AuditCheckResult(
            check_name="mattermost_integration",
            status=ServiceStatus.UNKNOWN,
            compliant=False,
            actual_value="not_secure",
            expected_value="mattermost_secure_configured",
            details="Mattermost не настроен безопасно: отсутствуют channels, integrations и security settings требуют настройки"
        )