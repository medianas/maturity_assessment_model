import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import argparse
from datetime import datetime
from unittest.mock import patch

from app import MaturityAssessmentApplication
from models import (
    SSHCredentials,
    AutomationExecutionReport,
    AutomationExecutionResult,
)

# --- Конфигурации кластеров ---
CLUSTERS = {
    "base": {
        "title": "Infrastructure Maturity Baseline",
        "description": "Базовый сценарий — три узла с возрастающей зрелостью",
        "nodes": [
            {"ip": "192.168.56.10", "name": "node-critical"},
            {"ip": "192.168.56.20", "name": "node-app"},
            {"ip": "192.168.56.30", "name": "node-secure"},
        ],
    },
    "lifecycle": {
        "title": "Production Lifecycle (dev → staging → prod)",
        "description": "Жизненный цикл сервиса: окружения разработки до продакшена",
        "nodes": [
            {"ip": "192.168.57.10", "name": "node-dev"},
            {"ip": "192.168.57.20", "name": "node-staging"},
            {"ip": "192.168.57.30", "name": "node-prod"},
        ],
    },
    "tiers": {
        "title": "Service Tiers (bastion / internal / public)",
        "description": "Разные роли узлов: jump host, внутренний, публичный",
        "nodes": [
            {"ip": "192.168.58.10", "name": "node-bastion"},
            {"ip": "192.168.58.20", "name": "node-internal"},
            {"ip": "192.168.58.30", "name": "node-public"},
        ],
    },
}

SSH_CREDS = SSHCredentials(username="demo", password="demo")
SEP = "=" * 65


def _mock_automation(action_plan, target_node) -> AutomationExecutionReport:
    """Симуляция Ansible: реальный аудит, но автоматизация — не модифицируем ВМ."""
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


def _print_cluster_summary(reports, nodes_info: list, cluster_title: str) -> None:
    print(f"\n{SEP}")
    print(f"  СВОДНАЯ ТАБЛИЦА — {cluster_title}")
    print(SEP)
    print(f"  {'Узел':<16} {'Имя':<16} {'ДО':<12} {'ПОСЛЕ':<12} {'Δ':<4} {'Соответствий'}")
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
    parser = argparse.ArgumentParser(description="Кластерная оценка зрелости DevSecOps")
    parser.add_argument(
        "cluster", nargs="?", default="base", choices=list(CLUSTERS.keys()),
        help="Какой кластер оценивать (по умолчанию: base)"
    )
    parser.add_argument(
        "--profile", default="admin", choices=["user", "default", "admin"],
        help="Профиль аудита"
    )
    args = parser.parse_args()

    cluster = CLUSTERS[args.cluster]
    nodes_info = cluster["nodes"]

    print(SEP)
    print(f"  Кластерная оценка зрелости — {cluster['title']}")
    print(f"  {cluster['description']}")
    print(f"  Узлов: {len(nodes_info)} | Профиль: {args.profile} | SSH: demo@<ip>")
    print(SEP)
    print()
    for info in nodes_info:
        print(f"  {info['ip']}  {info['name']}")

    app = MaturityAssessmentApplication()

    with patch.object(app.automation_manager, "execute_action_plan",
                      side_effect=_mock_automation):
        reports = app.initiate_maturity_assessment(
            ip_addresses=[n["ip"] for n in nodes_info],
            ssh_credentials=SSH_CREDS,
            profile=args.profile,
        )

    if not reports:
        print(f"\n[ERROR] Отчёты не получены. Убедитесь, что кластер '{args.cluster}' запущен:")
        print(f"  cd vagrant/cluster-{args.cluster} && vagrant up")
        sys.exit(1)

    for r, info in zip(reports, nodes_info):
        print(f"\n{SEP}")
        print(f"  УЗЕЛ: {r.node_ip}  ({info['name']})")
        print(SEP)
        _print_node_audit(r, info)

    _print_cluster_summary(reports, nodes_info, cluster["title"])

    print(f"\n{SEP}")
    print("  Кластерная оценка завершена")
    print(SEP)


if __name__ == "__main__":
    main()
