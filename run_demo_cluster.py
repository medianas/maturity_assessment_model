import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime
from unittest.mock import patch

from app import MaturityAssessmentApplication
from models import (
    SSHCredentials,
    AutomationExecutionReport,
    AutomationExecutionResult,
)

# --- Конфигурация кластера ---
CLUSTER_NODES = [
    {"ip": "192.168.56.10", "name": "node-critical", "profile": "admin"},
    {"ip": "192.168.56.20", "name": "node-app",      "profile": "admin"},
    {"ip": "192.168.56.30", "name": "node-secure",   "profile": "admin"},
]

SSH_CREDS = SSHCredentials(username="demo", password="demo")
SEP = "=" * 65


def _mock_automation(action_plan, target_node) -> AutomationExecutionReport:
    """Симуляция Ansible: реальный аудит + план, имитация применения плейбуков."""
    results = [
        AutomationExecutionResult(
            action_id=action.action_id,
            success=True,
            execution_time=1.3,
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


def _print_node_audit(report, node_info: dict) -> None:
    audit = getattr(report, "original_audit_report", None) or report.audit_report
    print(f"\n  Аудит ({len(audit.checks)} проверок):")
    for check in audit.checks:
        mark = "[OK]  " if check.compliant else "[FAIL]"
        print(f"    {mark} {check.check_name}: {check.details}")

    if report.correction_plan:
        print(f"\n  Запланировано корректирующих действий: {len(report.correction_plan.actions)}")
        for action in report.correction_plan.actions:
            print(f"    -> [{action.priority}] {action.description}")

    lvl_b = report.initial_maturity_level
    lvl_a = report.final_maturity_level
    delta = lvl_a.value - lvl_b.value
    delta_str = f"+{delta}" if delta > 0 else str(delta)
    print(f"\n  Уровень зрелости ДО:    {lvl_b.name} ({lvl_b.value}/5)")
    print(f"  Уровень зрелости ПОСЛЕ: {lvl_a.name} ({lvl_a.value}/5)  [{delta_str}]")


def _print_cluster_summary(reports, nodes_info: list) -> None:
    print(f"\n{SEP}")
    print("  СВОДНАЯ ТАБЛИЦА ПО КЛАСТЕРУ")
    print(SEP)
    hdr = f"  {'Узел':<16} {'Имя':<16} {'ДО':<12} {'ПОСЛЕ':<12} {'Δ':<4} {'Соответствий'}"
    print(hdr)
    print(f"  {'-'*16} {'-'*16} {'-'*12} {'-'*12} {'-'*4} {'-'*13}")

    total_before, total_after = 0, 0
    for r, info in zip(reports, nodes_info):
        lvl_b = r.initial_maturity_level
        lvl_a = r.final_maturity_level
        delta = lvl_a.value - lvl_b.value
        delta_str = f"+{delta}" if delta > 0 else str(delta)

        audit = getattr(r, "original_audit_report", None) or r.audit_report
        ok = sum(1 for c in audit.checks if c.compliant)
        total = len(audit.checks)

        print(f"  {r.node_ip:<16} {info['name']:<16} "
              f"{lvl_b.name:<12} {lvl_a.name:<12} {delta_str:<4} {ok}/{total}")

        total_before += lvl_b.value
        total_after  += lvl_a.value

    n = len(reports)
    avg_b = total_before / n
    avg_a = total_after  / n
    print(f"\n  Средний уровень ДО:    {avg_b:.1f} / 5")
    print(f"  Средний уровень ПОСЛЕ: {avg_a:.1f} / 5")
    print(f"  Среднее улучшение:    +{avg_a - avg_b:.1f} уровня по кластеру")


def main() -> None:
    print(SEP)
    print("  Кластерная оценка зрелости DevSecOps-инфраструктуры")
    print(f"  Узлов: {len(CLUSTER_NODES)} | Профиль: admin | SSH: demo@<ip>")
    print(SEP)
    print()
    for info in CLUSTER_NODES:
        print(f"  {info['ip']}  {info['name']}")

    app = MaturityAssessmentApplication()

    # Реальный аудит (SSH + порты), автоматизация — симуляция
    with patch.object(app.automation_manager, "execute_action_plan",
                      side_effect=_mock_automation):
        reports = app.initiate_maturity_assessment(
            ip_addresses=[n["ip"] for n in CLUSTER_NODES],
            ssh_credentials=SSH_CREDS,
            profile="admin",
        )

    if not reports:
        print("\n[ERROR] Отчёты не получены. Убедитесь, что Vagrant-кластер запущен:")
        print("  cd vagrant && vagrant up")
        sys.exit(1)

    # Вывод по каждому узлу
    for r, info in zip(reports, CLUSTER_NODES):
        print(f"\n{SEP}")
        print(f"  УЗЕЛ: {r.node_ip}  ({info['name']})")
        print(SEP)
        _print_node_audit(r, info)

    # Итоговая сводка
    _print_cluster_summary(reports, CLUSTER_NODES)

    print(f"\n{SEP}")
    print("  Кластерная оценка завершена")
    print(SEP)


if __name__ == "__main__":
    main()
