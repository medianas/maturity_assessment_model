# Импорт необходимых модулей для симуляции демонстрации
from functools import wraps

from app import MaturityAssessmentApplication
from models import SSHCredentials
import audit as audit_mod
import decision as decision_mod
import automation as automation_mod
import config as config_mod

# Проверка конфигурации инструментов DevOps
def check_devops_tools_configuration():
    print("\n--- Проверка конфигурации DevOps инструментов ---")
    
    deployment_params = config_mod.DEPLOYMENT_PARAMETERS
    
    gitlab = deployment_params.get("gitlab", {})
    gitlab_hostname = gitlab.get("hostname", "")
    gitlab_protocol = gitlab.get("protocol", "")
    if gitlab_hostname and gitlab_hostname != "gitlab.example.com" and gitlab_protocol == "https":
        print("[OK] GitLab: configured properly (hostname: {}, protocol: {})".format(gitlab_hostname, gitlab_protocol))
    else:
        print("[FAIL] GitLab: needs configuration (hostname: {}, protocol: {})".format(gitlab_hostname, gitlab_protocol))
    
    redmine = deployment_params.get("redmine", {})
    redmine_hostname = redmine.get("hostname", "")
    redmine_protocol = redmine.get("protocol", "")
    if redmine_hostname and redmine_hostname != "redmine.example.com" and redmine_protocol == "https":
        print("[OK] Redmine: configured properly (hostname: {}, protocol: {})".format(redmine_hostname, redmine_protocol))
    else:
        print("[FAIL] Redmine: needs configuration (hostname: {}, protocol: {})".format(redmine_hostname, redmine_protocol))
    
    communication = deployment_params.get("communication", {})
    mattermost_hostname = communication.get("mattermost_hostname", "")
    mattermost_protocol = communication.get("protocol", "")
    if mattermost_hostname and mattermost_hostname != "chat.example.com" and mattermost_protocol == "https":
        print("[OK] Mattermost: configured properly (hostname: {}, protocol: {})".format(mattermost_hostname, mattermost_protocol))
    else:
        print("[FAIL] Mattermost: needs configuration (hostname: {}, protocol: {})".format(mattermost_hostname, mattermost_protocol))
    
    print("--- Конец проверки конфигурации ---")

# Создание обертки для вызовов функций
def make_wrapper(func):
    desc = func.__doc__ or "No description available"

    @wraps(func)
    def wrapper(*args, **kwargs):
        print("--- CALL:")
        print(f"Function: {func.__qualname__}")
        print("Description:")
        for line in desc.strip().splitlines():
            safe_line = line.strip().replace('→', '->')
            print("  " + safe_line)
        result = func(*args, **kwargs)
        print(f"--- RETURN: {func.__qualname__}")
        return result

    return wrapper

# Обертка методов для демонстрации
def wrap_methods():
    App = MaturityAssessmentApplication
    for name in [
        'validate_input_parameters',
        '_prepare_target_nodes',
        '_execute_audit_phase',
        '_execute_decision_phase',
        '_execute_automation_phase',
        '_generate_final_reports',
        'generate_user_report',
        'export_report'
    ]:
        if hasattr(App, name):
            orig = getattr(App, name)
            setattr(App, name, make_wrapper(orig))

    Audit = audit_mod.InfrastructureAudit
    for name in [
        'audit_node_configuration',
        '_check_https_enabled',
        '_check_ssh_config',
        '_check_firewall',
        '_check_connectivity',
        '_check_gitlab_integration',
        '_check_redmine_integration',
        '_check_mattermost_integration'
    ]:
        if hasattr(Audit, name):
            orig = getattr(Audit, name)
            setattr(Audit, name, make_wrapper(orig))

    Decision = decision_mod.DecisionEngine
    for name in [
        'analyze_audit_results',
        'assess_maturity_level',
        'generate_recommendations'
    ]:
        if hasattr(Decision, name):
            orig = getattr(Decision, name)
            setattr(Decision, name, make_wrapper(orig))

    Ansible = automation_mod.AnsibleAutomationManager
    for name in [
        'execute_action_plan',
        'execute_single_action',
        '_run_playbook',
        'verify_idempotency',
        'rollback_changes',
        '_log_execution'
    ]:
        if hasattr(Ansible, name):
            orig = getattr(Ansible, name)
            setattr(Ansible, name, make_wrapper(orig))

# Основная функция демонстрации
def main():
    print("=== Simulation: user starts the maturity assessment ===")
    print("DevOps Tools Integration Active:")
    print("  - GitLab integration: CI/CD pipelines, security scanning")
    print("  - Redmine integration: issue tracking, project management")
    print("  - Mattermost integration: team communication, integrations")
    
    check_devops_tools_configuration()
    
    wrap_methods()

    app = MaturityAssessmentApplication()
    ip_addresses = ["192.168.1.10"]
    ssh_creds = SSHCredentials(username="admin", password="password")
    profile = "admin"

    print("[User] Press Start and provide inputs: IPs and SSH credentials")

    reports = app.initiate_maturity_assessment(
        ip_addresses=ip_addresses,
        ssh_credentials=ssh_creds,
        profile=profile
    )

    print("\n=== Simulation finished. Generated reports count:", len(reports))

    if reports:
        r = reports[0]
        print("\n--- Exported report (JSON) ---")
        print(app.export_report(r, format="json"))

    print("\n=== Demonstration: Retrieving saved reports ===")
    
    saved_reports = app.get_saved_reports()
    print(f"Total saved reports: {len(saved_reports)}")
    
    if saved_reports:
        print("\n--- List of saved reports ---")
        for report in saved_reports:
            print(f"ID: {report['id']}, Node: {report['node_ip']}, Timestamp: {report['timestamp']}")
        
        first_report_id = saved_reports[0]['id']
        detailed_report = app.get_report_by_id(first_report_id)
        if detailed_report:
            print(f"\n--- Detailed report for ID {first_report_id} ---")
            print(f"Node IP: {detailed_report['node_ip']}")
            print(f"Timestamp: {detailed_report['timestamp']}")
            print(f"Initial maturity: {detailed_report['report_data'].get('initial_maturity_level')}")
            print(f"Final maturity: {detailed_report['report_data'].get('final_maturity_level')}")
            print(f"Recommendations count: {len(detailed_report['report_data'].get('recommendations', []))}")
        
        node_reports = app.get_reports_by_node("192.168.1.10")
        print(f"Reports for node 192.168.1.10: {len(node_reports)}")
    
    print("\n=== End of demonstration ===")


if __name__ == '__main__':
    main()
