"""
Кластерная демонстрация с РЕАЛЬНЫМ запуском Ansible-плейбуков.

В отличие от run_demo_cluster.py (где автоматизация мокается),
этот скрипт:

  1. Делает реальный аудит target-узлов через paramiko + sockets.
  2. Decision Engine строит план действий.
  3. Плейбуки РЕАЛЬНО запускаются на control-node через SSH
     (см. automation_via_control.py).
  4. После применения делается ВТОРОЙ аудит — чтобы увидеть РЕАЛЬНОЕ
     изменение состояния ВМ.
  5. Сводная таблица: ДО → ПОСЛЕ с реальными числами compliant-checks.

Поддерживает 3 кластера:
  python run_demo_cluster_real.py base       (cluster-base)
  python run_demo_cluster_real.py lifecycle  (cluster-lifecycle)
  python run_demo_cluster_real.py tiers      (cluster-tiers)

Соответствующий кластер должен быть полностью поднят, включая node-control.
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import argparse

from app import MaturityAssessmentApplication
from automation_via_control import ControlNodeAutomationManager
from models import SSHCredentials


CLUSTERS = {
    "base": {
        "title": "Infrastructure Maturity Baseline",
        "control_host": "192.168.56.5",
        "nodes": [
            {"ip": "192.168.56.10", "name": "node-critical"},
            {"ip": "192.168.56.20", "name": "node-app"},
            {"ip": "192.168.56.30", "name": "node-secure"},
        ],
    },
    "lifecycle": {
        "title": "Production Lifecycle (dev → staging → prod)",
        "control_host": "192.168.57.5",
        "nodes": [
            {"ip": "192.168.57.10", "name": "node-dev"},
            {"ip": "192.168.57.20", "name": "node-staging"},
            {"ip": "192.168.57.30", "name": "node-prod"},
        ],
    },
    "tiers": {
        "title": "Service Tiers (bastion / internal / public)",
        "control_host": "192.168.58.5",
        "nodes": [
            {"ip": "192.168.58.10", "name": "node-bastion"},
            {"ip": "192.168.58.20", "name": "node-internal"},
            {"ip": "192.168.58.30", "name": "node-public"},
        ],
    },
}

SSH_CREDS = SSHCredentials(username="demo", password="demo")
SEP = "=" * 65


def _audit_only(app, ip_addresses):
    nodes = app._prepare_target_nodes(ip_addresses, SSH_CREDS, "admin")
    reports = app._execute_audit_phase(nodes)
    return {r.node_ip: r for r in reports}


def _summarize(audit_report):
    ok = sum(1 for c in audit_report.checks if c.compliant)
    return ok, len(audit_report.checks)


def main():
    parser = argparse.ArgumentParser(
        description="Кластерная оценка с РЕАЛЬНЫМ запуском Ansible на control-node"
    )
    parser.add_argument(
        "cluster", nargs="?", default="base", choices=list(CLUSTERS.keys()),
        help="Какой кластер прогонять (по умолчанию: base)"
    )
    args = parser.parse_args()

    cfg = CLUSTERS[args.cluster]
    nodes_info = cfg["nodes"]
    ip_list = [n["ip"] for n in nodes_info]

    print(SEP)
    print(f"  Кластерная оценка зрелости (РЕАЛЬНАЯ автоматизация)")
    print(f"  Кластер:      {args.cluster} — {cfg['title']}")
    print(f"  Control-node: {cfg['control_host']} (Ansible)")
    print(f"  Targets:      {ip_list}")
    print(SEP)

    app = MaturityAssessmentApplication()
    app.automation_manager = ControlNodeAutomationManager(
        control_host=cfg["control_host"],
        control_user="demo",
        control_password="demo",
    )

    print("\n[Шаг 1] Аудит ДО применения плейбуков...")
    before = _audit_only(app, ip_list)
    for n in nodes_info:
        ok, total = _summarize(before[n["ip"]])
        print(f"  {n['name']:<14} {n['ip']}: соответствий {ok}/{total}")

    print(f"\n[Шаг 2] Полный пайплайн с реальным Ansible-запуском...")
    reports = app.initiate_maturity_assessment(
        ip_addresses=ip_list,
        ssh_credentials=SSH_CREDS,
        profile="admin",
    )

    if not reports:
        print("\n[ERROR] Отчёты не получены")
        sys.exit(1)

    print(f"\n[Шаг 3] Аудит ПОСЛЕ применения плейбуков...")
    after = _audit_only(app, ip_list)
    for n in nodes_info:
        ok, total = _summarize(after[n["ip"]])
        print(f"  {n['name']:<14} {n['ip']}: соответствий {ok}/{total}")

    for r, info in zip(reports, nodes_info):
        print(f"\n{SEP}")
        print(f"  УЗЕЛ: {r.node_ip}  ({info['name']})")
        print(SEP)

        print("\n  --- Аудит ДО ---")
        for c in before[r.node_ip].checks:
            mark = "[OK]  " if c.compliant else "[FAIL]"
            print(f"    {mark} {c.check_name}: {c.details}")

        if r.correction_plan:
            print(f"\n  --- План действий ({len(r.correction_plan.actions)}) ---")
            for a in r.correction_plan.actions:
                print(f"    [P{a.priority}] {a.description} ({a.ansible_playbook})")

        if r.automation_report:
            print(f"\n  --- Результаты автоматизации ---")
            for ar in r.automation_report.results:
                m = "[OK]  " if ar.success else "[FAIL]"
                print(f"    {m} {ar.playbook} ({ar.execution_time:.1f}s)")

        print("\n  --- Аудит ПОСЛЕ ---")
        for c in after[r.node_ip].checks:
            mark = "[OK]  " if c.compliant else "[FAIL]"
            print(f"    {mark} {c.check_name}: {c.details}")

        ok_b, _ = _summarize(before[r.node_ip])
        ok_a, total = _summarize(after[r.node_ip])
        print(f"\n  Соответствий: {ok_b}/{total} → {ok_a}/{total}")
        print(f"  Уровень зрелости: "
              f"{r.initial_maturity_level.name}({r.initial_maturity_level.value}) → "
              f"{r.final_maturity_level.name}({r.final_maturity_level.value})")

    print(f"\n{SEP}")
    print(f"  СВОДНАЯ ТАБЛИЦА — {cfg['title']}")
    print(SEP)
    print(f"  {'Узел':<14} {'IP':<16} {'ДО':<10} {'ПОСЛЕ':<10} {'Δ checks'}")
    print(f"  {'-'*14} {'-'*16} {'-'*10} {'-'*10} {'-'*9}")

    total_b = total_a = 0
    for n in nodes_info:
        ok_b, total = _summarize(before[n["ip"]])
        ok_a, _ = _summarize(after[n["ip"]])
        delta = ok_a - ok_b
        total_b += ok_b
        total_a += ok_a
        delta_str = f"+{delta}" if delta > 0 else (f"{delta}" if delta < 0 else "0")
        print(f"  {n['name']:<14} {n['ip']:<16} {ok_b}/{total:<8} {ok_a}/{total:<8} {delta_str}")

    n = len(nodes_info)
    print(f"\n  Среднее compliance ДО:    {total_b/n:.1f} / 7")
    print(f"  Среднее compliance ПОСЛЕ: {total_a/n:.1f} / 7")
    print(f"  Среднее улучшение:        +{(total_a-total_b)/n:.1f} проверки на узел")

    print(f"\n{SEP}")
    print("  Прогон завершён")
    print(SEP)


if __name__ == "__main__":
    main()
