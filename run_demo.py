import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime
from unittest.mock import patch

from app import MaturityAssessmentApplication
from models import (
    SSHCredentials,
    AuditReport,
    AuditCheckResult,
    ServiceStatus,
    AutomationExecutionReport,
    AutomationExecutionResult,
)
import config as config_mod


SEPARATOR = "=" * 65


def check_devops_tools_configuration():
    print("\n--- Проверка конфигурации DevOps-инструментов ---")

    params = config_mod.DEPLOYMENT_PARAMETERS

    gitlab = params.get("gitlab", {})
    host, proto = gitlab.get("hostname", ""), gitlab.get("protocol", "")
    if host and host != "gitlab.example.com" and proto == "https":
        print(f"[OK]   GitLab: настроен ({host}, {proto})")
    else:
        print(f"[FAIL] GitLab: требует настройки (hostname: {host})")

    redmine = params.get("redmine", {})
    host, proto = redmine.get("hostname", ""), redmine.get("protocol", "")
    if host and host != "redmine.example.com" and proto == "https":
        print(f"[OK]   Redmine: настроен ({host}, {proto})")
    else:
        print(f"[FAIL] Redmine: требует настройки (hostname: {host})")

    comm = params.get("communication", {})
    host, proto = comm.get("mattermost_hostname", ""), comm.get("protocol", "")
    if host and host != "chat.example.com" and proto == "https":
        print(f"[OK]   Mattermost: настроен ({host}, {proto})")
    else:
        print(f"[FAIL] Mattermost: требует настройки (hostname: {host})")

    print("--- Конец проверки ---")


def _make_audit_report(node_ip: str) -> AuditReport:
    """Синтетический отчёт аудита с реалистичными нарушениями."""
    return AuditReport(
        node_ip=node_ip,
        timestamp=datetime.now().isoformat(),
        overall_status=ServiceStatus.RUNNING,
        checks=[
            AuditCheckResult(
                check_name="service_availability",
                status=ServiceStatus.RUNNING,
                compliant=True,
                actual_value="HTTP(80), SSH(22)",
                expected_value="HTTP/HTTPS/SSH available",
                details="Доступные сервисы: HTTP(80), SSH(22)",
            ),
            AuditCheckResult(
                check_name="https_enabled",
                status=ServiceStatus.RUNNING,
                compliant=False,
                actual_value="HTTP only",
                expected_value="HTTPS enabled",
                details="Только HTTP доступен, HTTPS отсутствует",
            ),
            AuditCheckResult(
                check_name="ssh_config",
                status=ServiceStatus.RUNNING,
                compliant=False,
                actual_value="RootLogin:yes, PasswordAuth:yes",
                expected_value="PermitRootLogin=no, PasswordAuthentication=no",
                details="SSH: root-доступ и парольная аутентификация разрешены",
            ),
            AuditCheckResult(
                check_name="firewall_status",
                status=ServiceStatus.STOPPED,
                compliant=False,
                actual_value="inactive",
                expected_value="active",
                details="Firewall установлен, но не активен",
            ),
            AuditCheckResult(
                check_name="gitlab_integration",
                status=ServiceStatus.RUNNING,
                compliant=False,
                actual_value="available_http_only",
                expected_value="available_with_https",
                details="GitLab доступен, но без HTTPS",
            ),
            AuditCheckResult(
                check_name="redmine_integration",
                status=ServiceStatus.STOPPED,
                compliant=False,
                actual_value="not_available",
                expected_value="available_with_https",
                details="Redmine недоступен на стандартных портах",
            ),
            AuditCheckResult(
                check_name="mattermost_integration",
                status=ServiceStatus.STOPPED,
                compliant=False,
                actual_value="not_available",
                expected_value="available_with_https",
                details="Mattermost недоступен на стандартных портах",
            ),
        ],
    )


def _make_automation_report(action_plan, target_node) -> AutomationExecutionReport:
    """Успешный результат выполнения плейбуков (симуляция Ansible)."""
    results = [
        AutomationExecutionResult(
            action_id=action.action_id,
            success=True,
            execution_time=1.4,
            stdout=f"changed: [{target_node.ip_address}]",
            stderr="",
            idempotent=True,
            playbook=action.ansible_playbook,
        )
        for action in action_plan.actions
    ]
    return AutomationExecutionReport(
        node_ip=target_node.ip_address,
        timestamp=datetime.now().isoformat(),
        results=results,
        all_successful=True,
    )


def _print_audit_summary(audit_report: AuditReport):
    print(f"\n  Результаты аудита ({len(audit_report.checks)} проверок):")
    for check in audit_report.checks:
        mark = "[OK]  " if check.compliant else "[FAIL]"
        print(f"    {mark} {check.check_name}: {check.details}")


def _print_plan_summary(plan):
    if plan is None:
        print("  Нарушений не обнаружено — план коррекции не требуется")
        return
    print(f"  Несоответствий: {len(plan.non_compliant_checks)}, "
          f"запланировано действий: {len(plan.actions)}")
    for action in plan.actions:
        print(f"    -> [{action.priority}] {action.description}")
        print(f"       Плейбук: {action.ansible_playbook}")


def _print_automation_summary(report: AutomationExecutionReport):
    status = "Успешно" if report.all_successful else "С ошибками"
    print(f"  Статус: {status} ({len(report.results)} плейбуков выполнено)")
    for r in report.results:
        mark = "[OK]  " if r.success else "[ERROR]"
        idm = "идемпотентно" if r.idempotent else "не идемпотентно"
        print(f"    {mark} {r.playbook} — {r.execution_time:.1f}с, {idm}")


def main():
    print(SEPARATOR)
    print("  Система оценки зрелости DevSecOps-инфраструктуры")
    print("  Дипломная работа — демонстрация")
    print(SEPARATOR)

    print("\nАктивные интеграции:")
    print("  - GitLab:     CI/CD-конвейеры, security-scanning")
    print("  - Redmine:    отслеживание задач, управление проектами")
    print("  - Mattermost: командная коммуникация, уведомления")

    check_devops_tools_configuration()

    app = MaturityAssessmentApplication()
    ip_addresses = ["192.168.1.10"]
    ssh_creds = SSHCredentials(username="admin", password="demo")
    profile = "admin"

    print(f"\n[Пользователь] Запуск оценки зрелости")
    print(f"  Узел:    {ip_addresses[0]}")
    print(f"  Профиль: {profile} (полный набор проверок DevSecOps)")

    with patch.object(
        app.audit_module,
        "audit_node_configuration",
        side_effect=lambda node, _: _make_audit_report(node.ip_address),
    ), patch.object(
        app.automation_manager,
        "execute_action_plan",
        side_effect=_make_automation_report,
    ):
        reports = app.initiate_maturity_assessment(
            ip_addresses=ip_addresses,
            ssh_credentials=ssh_creds,
            profile=profile,
        )

    if not reports:
        print("\n[ERROR] Отчёты не сформированы")
        return

    r = reports[0]

    # Детальный вывод по фазам
    print("\n" + SEPARATOR)
    print("  ФАЗА 1 — Результаты аудита")
    print(SEPARATOR)
    _print_audit_summary(r.original_audit_report or r.audit_report)

    print("\n" + SEPARATOR)
    print("  ФАЗА 2 — План корректирующих действий")
    print(SEPARATOR)
    _print_plan_summary(r.correction_plan)

    print("\n" + SEPARATOR)
    print("  ФАЗА 3 — Выполнение автоматизации (Ansible)")
    print(SEPARATOR)
    if r.automation_report:
        _print_automation_summary(r.automation_report)
    else:
        print("  Автоматизация не потребовалась")

    print("\n" + SEPARATOR)
    print("  ИТОГ")
    print(SEPARATOR)
    lvl_before = r.initial_maturity_level
    lvl_after = r.final_maturity_level
    print(f"  Уровень зрелости ДО:   {lvl_before.name} ({lvl_before.value}/5)")
    print(f"  Уровень зрелости ПОСЛЕ: {lvl_after.name} ({lvl_after.value}/5)")

    if r.recommendations:
        print("\n  Рекомендации для оператора:")
        for i, rec in enumerate(r.recommendations[:5], 1):
            print(f"    {i}. {rec}")

    print("\n" + SEPARATOR)
    print("  ЭКСПОРТ ОТЧЁТА (JSON)")
    print(SEPARATOR)
    print(app.export_report(r, format="json"))

    print("\n" + SEPARATOR)
    print("  ИСТОРИЯ ОТЧЁТОВ (БД)")
    print(SEPARATOR)
    saved = app.get_saved_reports()
    print(f"  Всего сохранено: {len(saved)}")
    for rep in saved[:5]:
        print(f"    ID {rep['id']:>3} | {rep['node_ip']:<15} | {rep['timestamp']}")

    print("\n" + SEPARATOR)
    print("  Демонстрация завершена")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
