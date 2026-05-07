"""
Быстрая sanity-проверка кода audit.py без необходимости полного bootstrap'а
Vagrant-кластера. Имитирует ответы сервисов через моки и убеждается что
все 10 проверок профиля admin отрабатывают корректно.

Используется как дополнение к pytest для быстрой проверки итерации работы
с audit-кодом.

Запуск: python quick_audit_check.py
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from unittest.mock import patch
from audit import InfrastructureAudit
from models import TargetNode, SSHCredentials


SCENARIOS = {
    "missing": {
        "name": "missing — сервисы не установлены",
        "ports": {22: True, 80: False, 443: False, 3000: False, 8065: False, 8080: False},
        "http": {-1: True},  # все HTTP-вызовы вернут ошибку
        "ssh_config": "PermitRootLogin yes\nPasswordAuthentication yes",
        "ufw": "inactive",
        "expected_compliant": ["service_availability"],
        "expected_failed": [
            "https_enabled", "ssh_config", "firewall_status",
            "gitlab_integration", "redmine_integration", "mattermost_integration",
            "gitlab_redmine_link", "gitlab_mattermost_link", "redmine_mattermost_link",
        ],
    },
    "broken": {
        "name": "broken — сервисы стоят, без HTTPS, без webhooks",
        "ports": {22: True, 80: True, 443: False, 3000: True, 8065: True, 8080: False},
        "http_https": (-1, "ssl error"),
        "http_plain": (200, "_placeholder_"),
        "ssh_config": "PermitRootLogin yes\nPasswordAuthentication yes",
        "ufw": "active",
        "expected_compliant": ["service_availability", "firewall_status"],
        "expected_failed": [
            "https_enabled", "ssh_config",
            "gitlab_integration", "redmine_integration", "mattermost_integration",
            "gitlab_redmine_link", "gitlab_mattermost_link", "redmine_mattermost_link",
        ],
    },
    "ok": {
        "name": "ok — всё работает",
        "ports": {22: True, 80: True, 443: True, 3000: True, 8065: True, 8080: True},
        "http_https": (200, "_placeholder_"),
        "ssh_config": "PermitRootLogin no\nPasswordAuthentication no",
        "ufw": "active",
        "marker_present": True,
        "expected_compliant": [
            "service_availability", "https_enabled", "ssh_config", "firewall_status",
            "gitlab_integration", "redmine_integration", "mattermost_integration",
            "gitlab_redmine_link", "gitlab_mattermost_link", "redmine_mattermost_link",
        ],
        "expected_failed": [],
    },
}


def run_scenario(name: str, scenario: dict) -> bool:
    print(f"\n=== Scenario: {scenario['name']} ===")
    audit = InfrastructureAudit()
    creds = SSHCredentials(username="demo", password="demo")
    node = TargetNode(ip_address="192.168.56.10", ssh_credentials=creds, profile="admin")

    def fake_port_open(host, port, timeout=5.0):
        return scenario["ports"].get(port, False)

    def fake_http_get(url, timeout=6.0, headers=None):
        # Контент зависит от endpoint'а — чтобы соответствовать парсерам audit'а
        if "/api/v4/version" in url:
            body = '{"version":"16.11.10"}'
        elif "/api/v4/system/ping" in url:
            body = '{"status":"OK"}'
        else:  # Redmine "/" — ищет «Redmine» в HTML
            body = "<html><title>Redmine</title></html>"

        if "https://" in url:
            base = scenario.get("http_https", (-1, "no https"))
        else:
            base = scenario.get("http_plain", (-1, "no http"))
        # base = (status, _placeholder_body); подменяем body на правильный
        return (base[0], body if base[0] == 200 else base[1])

    def fake_ssh_check(node_arg, marker_path):
        if scenario.get("marker_present"):
            return True, f"link configured at {marker_path}"
        return False, ""

    def fake_find_ip(service):
        return "192.168.56.10"  # любой узел в кластере

    # Мок paramiko — ssh_config / firewall возвращают синтетические ответы
    class FakeSSH:
        def set_missing_host_key_policy(self, p): pass
        def connect(self, *a, **kw): pass
        def close(self): pass
        def exec_command(self, cmd):
            class Stdout:
                def __init__(self, payload):
                    self.payload = payload.encode()
                def read(self):
                    return self.payload
            if "sshd_config" in cmd:
                return None, Stdout(scenario["ssh_config"]), None
            if "ufw" in cmd:
                return None, Stdout(scenario["ufw"]), None
            return None, Stdout(""), None

    with patch.object(audit, "_check_port_open", side_effect=fake_port_open), \
         patch.object(audit, "_http_get", side_effect=fake_http_get), \
         patch.object(audit, "_check_link_marker_via_ssh", side_effect=fake_ssh_check), \
         patch.object(audit, "_find_service_ip", side_effect=fake_find_ip), \
         patch("paramiko.SSHClient", FakeSSH):
        report = audit.audit_node_configuration(node, "admin")

    actual_compliant = [c.check_name for c in report.checks if c.compliant]
    actual_failed = [c.check_name for c in report.checks if not c.compliant]

    expected_c = set(scenario["expected_compliant"])
    expected_f = set(scenario["expected_failed"])
    actual_c = set(actual_compliant)
    actual_f = set(actual_failed)

    print(f"  Compliant ({len(actual_c)}/10): {sorted(actual_c)}")
    print(f"  Failed    ({len(actual_f)}/10): {sorted(actual_f)}")

    if actual_c == expected_c and actual_f == expected_f:
        print(f"  [OK] Сценарий {name!r} соответствует ожиданиям")
        return True
    else:
        print(f"  [FAIL] Расхождение:")
        if expected_c - actual_c:
            print(f"    Должны были пройти, но провалились: {expected_c - actual_c}")
        if actual_c - expected_c:
            print(f"    Прошли неожиданно: {actual_c - expected_c}")
        return False


def main():
    print("Quick sanity-check audit.py (10 проверок admin-профиля)")
    print("=" * 60)
    results = {}
    for name, scenario in SCENARIOS.items():
        results[name] = run_scenario(name, scenario)

    print("\n" + "=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"  Итог: {passed}/{total} сценариев прошли")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
