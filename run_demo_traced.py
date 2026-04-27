"""
Подробный демо-сценарий с трассировкой вызовов методов (CALL/RETURN).

Назначение: показывает, ЧТО происходит ВНУТРИ приложения при каждом запуске
            (а не только итог). Все ключевые методы оборачиваются в декоратор,
            который печатает имя функции, описание из docstring, аргументы
            и возвращаемое значение.

Запуск:    python run_demo_traced.py

Этот файл не заменяет run_demo.py — он его дополняет. run_demo.py показывает
красивый итог пользователю; run_demo_traced.py — внутренний трассировочный
вывод для защиты диплома (соответствует Приложению А отчёта).
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime
from unittest.mock import patch

from app import MaturityAssessmentApplication
from audit import InfrastructureAudit
from decision import DecisionEngine
from automation import AnsibleAutomationManager
from models import (
    SSHCredentials,
    AuditReport,
    AuditCheckResult,
    ServiceStatus,
    AutomationExecutionReport,
    AutomationExecutionResult,
)
import config as config_mod


# ---------------------------------------------------------------------------
# Описания методов для трассировки (соответствуют Приложению А отчёта).
# Хранятся явно, не парсятся из docstring — это надёжнее и не зависит
# от состояния документации в коде.
# ---------------------------------------------------------------------------

METHOD_DESCRIPTIONS = {
    # ===== MaturityAssessmentApplication =====
    "MaturityAssessmentApplication.validate_input_parameters": {
        "description": "валидация входных параметров от пользователя.",
        "args": [
            "ip_addresses: список IP адресов целевых узлов",
            "ssh_credentials: учётные данные SSH",
            "profile: профиль проверки",
        ],
        "returns": "True если все параметры валидны, иначе False",
    },
    "MaturityAssessmentApplication._prepare_target_nodes": {
        "description": "внутренний метод для подготовки целевых узлов.",
        "args": [
            "ip_addresses: список IP адресов",
            "ssh_credentials: SSH учётные данные",
            "profile: профиль проверки",
        ],
        "returns": "список целевых узлов",
    },
    "MaturityAssessmentApplication._execute_audit_phase": {
        "description": (
            "внутренний метод для выполнения фазы аудита. Получает информацию "
            "о состоянии инфраструктуры и выявляет отклонения.\n"
            "Проверяет:\n"
            "- доступность сервисов и используемые протоколы (HTTP/HTTPS);\n"
            "- наличие механизмов защищенной конфигурации;\n"
            "- корректность параметров развертывания;\n"
            "- возможность воспроизводимого развертывания;\n"
            "- соблюдение требований безопасной архитектуры."
        ),
        "args": ["nodes: список целевых узлов"],
        "returns": "список отчётов аудита",
    },
    "MaturityAssessmentApplication._execute_decision_phase": {
        "description": (
            "внутренний метод для выполнения фазы принятия решений. Анализирует "
            "результаты аудита и формирует план корректирующих действий.\n"
            "Функции:\n"
            "- сопоставление результатов аудита с критериями зрелости;\n"
            "- определение набора управляющих воздействий;\n"
            "- формирование плана реакции с Ansible плейбуками;\n"
            "- определение порядка выполнения шагов."
        ),
        "args": ["audit_reports: список отчётов аудита"],
        "returns": (
            "список планов корректирующих действий "
            "(может содержать None если нарушений нет)"
        ),
    },
    "MaturityAssessmentApplication._execute_automation_phase": {
        "description": (
            "внутренний метод для выполнения фазы автоматизации. Применяет "
            "идемпотентные Ansible-плейбуки для исправления обнаруженных проблем.\n"
            "Функции:\n"
            "- выполнение конфигурационного управления (настройка сервисов);\n"
            "- применение безопасных параметров (HTTPS, SSH);\n"
            "- обеспечение идемпотентности;\n"
            "- логирование примененных шагов и результатов."
        ),
        "args": [
            "nodes: список целевых узлов",
            "action_plans: список планов корректирующих действий",
        ],
        "returns": "список отчётов о выполнении автоматизации (может содержать None)",
    },
    "MaturityAssessmentApplication._generate_final_reports": {
        "description": (
            "внутренний метод для генерирования итоговых отчётов. Агрегирует "
            "результаты всех фаз в единый отчёт для каждого узла.\n"
            "Включает:\n"
            "- начальный и финальный уровень зрелости;\n"
            "- список обнаруженных несоответствий;\n"
            "- статус выполнения исправлений;\n"
            "- рекомендации для оператора."
        ),
        "args": [
            "nodes: список целевых узлов",
            "audit_reports: результаты аудита",
            "action_plans: планы корректирующих действий",
            "automation_reports: результаты автоматизации",
        ],
        "returns": "список итоговых отчётов об оценке зрелости",
    },
    "MaturityAssessmentApplication.generate_user_report": {
        "description": (
            "сгенерировать наглядный отчёт для пользователя.\n"
            "Отображение результатов:\n"
            "- список обнаруженных несоответствий;\n"
            "- интерпретация несоответствий как признаков уровня зрелости;\n"
            "- статус выполнения исправлений;\n"
            "- рекомендации для улучшения инфраструктуры."
        ),
        "args": ["assessment_report: отчёт об оценке зрелости"],
        "returns": "словарь с информацией для представления пользователю",
    },
    "MaturityAssessmentApplication.export_report": {
        "description": (
            "экспортировать отчёт в различных форматах.\n"
            "Поддерживаемые форматы:\n"
            "- json: структурированный JSON\n"
            "- html: HTML отчёт для просмотра в браузере"
        ),
        "args": [
            "assessment_report: отчёт об оценке зрелости",
            "format: формат экспорта (json, html)",
        ],
        "returns": "строка с содержимым отчёта",
    },

    # ===== InfrastructureAudit =====
    "InfrastructureAudit.audit_node_configuration": {
        "description": "выполнить аудит конфигурации узла.",
        "args": [
            "node: целевой узел",
            "profile: профиль аудита",
        ],
        "returns": "AuditReport с результатами всех проверок",
    },
    "InfrastructureAudit._check_service_availability": {
        "description": "проверка доступности базовых сервисов (HTTP/HTTPS/SSH).",
    },
    "InfrastructureAudit._check_https_enabled": {"description": "проверка HTTPS."},
    "InfrastructureAudit._check_ssh_config": {"description": "проверка конфигурации SSH."},
    "InfrastructureAudit._check_firewall": {"description": "проверка firewall."},
    "InfrastructureAudit._check_connectivity": {"description": "проверка сетевой доступности узла."},
    "InfrastructureAudit._check_gitlab_integration": {"description": "проверка интеграции с GitLab."},
    "InfrastructureAudit._check_redmine_integration": {"description": "проверка интеграции с Redmine."},
    "InfrastructureAudit._check_mattermost_integration": {"description": "проверка интеграции с Mattermost."},

    # ===== DecisionEngine =====
    "DecisionEngine.analyze_audit_results": {
        "description": (
            "анализ результатов аудита и формирование плана действий.\n"
            "Применяет логические правила для:\n"
            "- выявления несоответствий (проверки, которые провалились);\n"
            "- определения набора корректирующих действий;\n"
            "- формирования последовательности действий с приоритетами;\n"
            "- оценки уровня зрелости инфраструктуры."
        ),
        "args": ["audit_report: отчёт аудита с результатами всех проверок"],
        "returns": "план корректирующих действий или None если нарушений не обнаружено",
    },
    "DecisionEngine.assess_maturity_level": {
        "description": (
            "определить уровень зрелости на основе 10 критериев зрелости.\n"
            "Критерии зрелости (синтез CMMI, DevSecOps, Agile, SPM):\n"
            "1. Повторяемость инфраструктуры.\n"
            "2. Автоматизированное развертывание.\n"
            "3. Интеграция безопасности по принципу shift-left.\n"
            "4. Соответствие эталонным конфигурациям безопасности.\n"
            "5. Автоматизированная реакция на несоответствия.\n"
            "6. Связанность инструментов жизненного цикла.\n"
            "7. Прозрачность и наблюдаемость процессов.\n"
            "8. Политики управления и контроля в коде.\n"
            "9. Управляемость изменений инфраструктуры.\n"
            "10. Масштабируемость инфраструктурных практик.\n"
            "Уровень зрелости определяется по фактам: уровень с максимальным "
            "количеством критериев."
        ),
        "args": ["audit_report: отчёт аудита"],
        "returns": "уровень зрелости инфраструктуры",
    },
    "DecisionEngine.generate_recommendations": {
        "description": "сгенерировать рекомендации для оператора.",
        "args": ["audit_report: отчёт аудита"],
        "returns": "список рекомендаций",
    },

    # ===== AnsibleAutomationManager =====
    "AnsibleAutomationManager.execute_action_plan": {
        "description": (
            "выполнить план корректирующих действий. Применяет идемпотентные "
            "Ansible-плейбуки в правильном порядке."
        ),
        "args": [
            "action_plan: план корректирующих действий",
            "target_node: целевой узел",
        ],
        "returns": "отчёт о выполнении автоматизации",
    },
    "AnsibleAutomationManager.execute_single_action": {
        "description": (
            "выполнить одно корректирующее действие. Запускает Ansible "
            "плейбук или роль идемпотентно."
        ),
        "args": [
            "action: корректирующее действие",
            "target_node: целевой узел",
        ],
        "returns": "результат выполнения",
    },
    "AnsibleAutomationManager._run_playbook": {
        "description": (
            "запустить Ansible-плейбук на целевом хосте. Плейбуки "
            "обеспечивают идемпотентное конфигурационное управление."
        ),
        "args": [
            "playbook_path: путь к плейбуку",
            "target_host: IP адрес целевого хоста",
            "extra_vars: дополнительные переменные для плейбука",
        ],
        "returns": "результат выполнения",
    },
    "AnsibleAutomationManager.verify_idempotency": {
        "description": (
            "проверить идемпотентность действия. Идемпотентное действие: "
            "повторное применение не изменяет результат."
        ),
        "args": [
            "action: корректирующее действие",
            "target_node: целевой узел",
        ],
        "returns": "True если действие идемпотентно",
    },
    "AnsibleAutomationManager._log_execution": {
        "description": (
            "логирование результатов выполнения, ведёт журнал изменений: "
            "что именно изменено, когда и почему."
        ),
        "args": [
            "action_id: идентификатор узла или действия",
            "report: отчёт о выполнении",
        ],
    },
}


def _format_call(qualified_name: str) -> str:
    info = METHOD_DESCRIPTIONS.get(qualified_name, {})
    out = ["--- CALL:", f"Function: {qualified_name}"]
    if info.get("description"):
        out.append(f"Description: {info['description']}")
    if info.get("args"):
        out.append("Args:")
        for arg in info["args"]:
            out.append(arg)
    if info.get("returns"):
        out.append(f"Returns: {info['returns']}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Декоратор для трассировки методов
# ---------------------------------------------------------------------------

_TRACED = []  # (cls, method_name, original)


def _trace(cls, method_name: str) -> None:
    """Оборачивает cls.method_name так, чтобы при каждом вызове печаталось
    CALL: ... RETURN: ..."""
    original = getattr(cls, method_name)
    qualified = f"{cls.__name__}.{method_name}"

    def wrapped(*args, **kwargs):
        print(_format_call(qualified))
        try:
            result = original(*args, **kwargs)
        except Exception as exc:
            print(f"--- RAISE: {qualified} ({type(exc).__name__}: {exc})")
            raise
        print(f"--- RETURN: {qualified}")
        return result

    wrapped.__name__ = original.__name__
    setattr(cls, method_name, wrapped)
    _TRACED.append((cls, method_name, original))


def _trace_all() -> None:
    """Список методов для трассировки (соответствует Приложению А отчёта)."""
    targets = {
        MaturityAssessmentApplication: [
            "validate_input_parameters",
            "_prepare_target_nodes",
            "_execute_audit_phase",
            "_execute_decision_phase",
            "_execute_automation_phase",
            "_generate_final_reports",
            "generate_user_report",
            "export_report",
        ],
        InfrastructureAudit: [
            "audit_node_configuration",
            "_check_service_availability",
            "_check_https_enabled",
            "_check_ssh_config",
            "_check_firewall",
            "_check_connectivity",
            "_check_gitlab_integration",
            "_check_redmine_integration",
            "_check_mattermost_integration",
        ],
        DecisionEngine: [
            "analyze_audit_results",
            "assess_maturity_level",
            "generate_recommendations",
        ],
        AnsibleAutomationManager: [
            "execute_action_plan",
            "execute_single_action",
            "_run_playbook",
            "verify_idempotency",
            "_log_execution",
        ],
    }
    for cls, methods in targets.items():
        for m in methods:
            if hasattr(cls, m):
                _trace(cls, m)


def _untrace_all() -> None:
    """Откатывает все patch'и (для повторных запусков в одном процессе)."""
    while _TRACED:
        cls, name, original = _TRACED.pop()
        setattr(cls, name, original)


# ---------------------------------------------------------------------------
# Синтетические аудит/автоматизация (как в run_demo.py)
# ---------------------------------------------------------------------------

def _make_audit_report(node_ip: str) -> AuditReport:
    return AuditReport(
        node_ip=node_ip,
        timestamp=datetime.now().isoformat(),
        overall_status=ServiceStatus.RUNNING,
        checks=[
            AuditCheckResult(
                check_name="service_availability",
                status=ServiceStatus.RUNNING, compliant=True,
                actual_value="HTTP(80), SSH(22)",
                expected_value="HTTP/HTTPS/SSH available",
                details="Доступные сервисы: HTTP(80), SSH(22)",
            ),
            AuditCheckResult(
                check_name="https_enabled",
                status=ServiceStatus.RUNNING, compliant=False,
                actual_value="HTTP only", expected_value="HTTPS enabled",
                details="Только HTTP доступен, HTTPS отсутствует",
            ),
            AuditCheckResult(
                check_name="ssh_config",
                status=ServiceStatus.RUNNING, compliant=False,
                actual_value="RootLogin:yes, PasswordAuth:yes",
                expected_value="PermitRootLogin=no, PasswordAuthentication=no",
                details="SSH: root-доступ и парольная аутентификация разрешены",
            ),
            AuditCheckResult(
                check_name="firewall_status",
                status=ServiceStatus.STOPPED, compliant=False,
                actual_value="inactive", expected_value="active",
                details="Firewall установлен, но не активен",
            ),
            AuditCheckResult(
                check_name="gitlab_integration",
                status=ServiceStatus.RUNNING, compliant=False,
                actual_value="available_http_only",
                expected_value="available_with_https",
                details="GitLab доступен, но без HTTPS",
            ),
            AuditCheckResult(
                check_name="redmine_integration",
                status=ServiceStatus.STOPPED, compliant=False,
                actual_value="not_available",
                expected_value="available_with_https",
                details="Redmine недоступен на стандартных портах",
            ),
            AuditCheckResult(
                check_name="mattermost_integration",
                status=ServiceStatus.STOPPED, compliant=False,
                actual_value="not_available",
                expected_value="available_with_https",
                details="Mattermost недоступен на стандартных портах",
            ),
        ],
    )


def _make_automation_report(action_plan, target_node) -> AutomationExecutionReport:
    return AutomationExecutionReport(
        node_ip=target_node.ip_address,
        timestamp=datetime.now().isoformat(),
        results=[
            AutomationExecutionResult(
                action_id=action.action_id,
                success=True,
                execution_time=0.5,
                stdout=f"changed: [{target_node.ip_address}]",
                stderr="",
                idempotent=True,
                playbook=action.ansible_playbook,
            )
            for action in action_plan.actions
        ],
        all_successful=True,
    )


# ---------------------------------------------------------------------------
# Проверка конфигурации DevOps-инструментов
# ---------------------------------------------------------------------------

def check_devops_tools_configuration():
    print("\n--- Проверка конфигурации DevOps-инструментов ---")
    params = config_mod.DEPLOYMENT_PARAMETERS

    gitlab = params.get("gitlab", {})
    host, proto = gitlab.get("hostname", ""), gitlab.get("protocol", "")
    if host and host != "gitlab.example.com" and proto == "https":
        print(f"[OK]   GitLab: настроен ({host}, {proto})")
    else:
        print(f"[FAIL] GitLab: требует настройки (hostname: {host}, protocol: {proto})")

    redmine = params.get("redmine", {})
    host, proto = redmine.get("hostname", ""), redmine.get("protocol", "")
    if host and host != "redmine.example.com" and proto == "https":
        print(f"[OK]   Redmine: настроен ({host}, {proto})")
    else:
        print(f"[FAIL] Redmine: требует настройки (hostname: {host}, protocol: {proto})")

    comm = params.get("communication", {})
    host, proto = comm.get("mattermost_hostname", ""), comm.get("protocol", "")
    if host and host != "chat.example.com" and proto == "https":
        print(f"[OK]   Mattermost: настроен ({host}, {proto})")
    else:
        print(f"[FAIL] Mattermost: требует настройки (hostname: {host}, protocol: {proto})")

    print("--- Конец проверки конфигурации ---")


# ---------------------------------------------------------------------------
# Основной сценарий
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== Simulation: user starts the maturity assessment ===")
    print("DevOps Tools Integration Active:")
    print("  - GitLab integration: CI/CD pipelines, security scanning;")
    print("  - Redmine integration: issue tracking, project management;")
    print("  - Mattermost integration: team communication, integrations.")

    check_devops_tools_configuration()

    print("[User] Press Start and provide inputs: IPs and SSH credentials")

    # Включаем трассировку
    _trace_all()
    try:
        app = MaturityAssessmentApplication()
        ip_addresses = ["192.168.1.10"]
        ssh_creds = SSHCredentials(username="admin", password="demo")
        profile = "admin"

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

        print(f"\n=== Simulation finished. Generated reports count: {len(reports)} ===")

        if not reports:
            print("[ERROR] Отчёты не сформированы")
            return

        print("\n--- Exported report (JSON) ---")
        print(app.export_report(reports[0], format="json"))

        print("\n=== Demonstration: Retrieving saved reports ===")
        saved = app.get_saved_reports()
        print(f"Total saved reports: {len(saved)}")
        print("--- List of saved reports ---")
        for rep in saved[:12]:
            print(f"ID: {rep['id']}, Node: {rep['node_ip']}, Timestamp: {rep['timestamp']}")

        if saved:
            top = saved[0]
            full = app.get_report_by_id(top["id"])
            print(f"\n--- Detailed report for ID {top['id']} ---")
            if full:
                rep_data = full.get("report_data", {})
                print(f"Node IP: {rep_data.get('node_ip')}")
                print(f"Timestamp: {rep_data.get('timestamp')}")
                print(f"Initial maturity: {rep_data.get('initial_maturity_level')}")
                print(f"Final maturity: {rep_data.get('final_maturity_level')}")
                recs = rep_data.get("recommendations", []) or []
                print(f"Recommendations count: {len(recs)}")

            node_ip = saved[0]["node_ip"]
            node_reports = app.get_reports_by_node(node_ip)
            print(f"Reports for node {node_ip}: {len(node_reports)}")

        print("=== End of demonstration ===")
    finally:
        _untrace_all()


if __name__ == "__main__":
    main()
