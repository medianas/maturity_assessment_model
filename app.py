from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from models import (
    TargetNode,
    SSHCredentials,
    MaturityAssessmentReport,
    MaturityLevel,
    AuditReport,
    AuditCheckResult,
    ServiceStatus,
    CorrectiveActionPlan,
    AutomationExecutionReport
)
from audit import InfrastructureAudit
from decision import DecisionEngine
from automation import AnsibleAutomationManager
from database import ReportDatabase
from config import AUDIT_PROFILES, MATURITY_RECOMMENDATIONS, CORRECTION_RULES

# Основной класс приложения для оценки зрелости
class MaturityAssessmentApplication:
    
    def __init__(self):
        self.audit_module = InfrastructureAudit()
        self.decision_engine = DecisionEngine()
        self.automation_manager = AnsibleAutomationManager()
        self.database = ReportDatabase()
        self.reports: List[MaturityAssessmentReport] = []
        self._supported_profiles = list(AUDIT_PROFILES.keys())
        
        self._check_to_correction = {
            "https_enabled": "https_not_enabled",
            "ssh_config": "insecure_ssh_config",
            "firewall_status": "firewall_misconfigured",
            "gitlab_integration": "gitlab_not_secure",
            "redmine_integration": "redmine_not_secure",
            "mattermost_integration": "mattermost_not_secure"
        }
    
    def validate_input_parameters(
        self,
        ip_addresses: List[str],
        ssh_credentials: SSHCredentials,
        profile: str
    ) -> bool:
        if not ip_addresses or len(ip_addresses) == 0:
            print("Ошибка: не указаны IP адреса целевых узлов")
            return False
        
        if not ssh_credentials.username:
            print("Ошибка: не указано имя пользователя SSH")
            return False
        
        if not ssh_credentials.password and not ssh_credentials.private_key_path:
            print("Ошибка: необходимо указать пароль или путь к приватному ключу SSH")
            return False
        
        if profile not in self._supported_profiles:
            print(f"Ошибка: неподдерживаемый профиль '{profile}'")
            print(f"Доступные профили: {', '.join(self._supported_profiles)}")
            return False
        
        return True
    
    # Основной метод для инициации процесса оценки зрелости
    def initiate_maturity_assessment(
        self,
        ip_addresses: List[str],
        ssh_credentials: SSHCredentials,
        profile: str
    ) -> List[MaturityAssessmentReport]:
        if not self.validate_input_parameters(ip_addresses, ssh_credentials, profile):
            return []
        
        print(f"\n[ФАЗА 1] Подготовка целевых узлов...")
        nodes = self._prepare_target_nodes(ip_addresses, ssh_credentials, profile)
        
        print(f"\n[ФАЗА 2] Выполнение аудита инфраструктуры...")
        audit_reports = self._execute_audit_phase(nodes)
        
        print(f"\n[ФАЗА 3] Анализ результатов и формирование плана действий...")
        action_plans = self._execute_decision_phase(audit_reports)
        
        print(f"\n[ФАЗА 4] Автоматизированное применение исправлений...")
        automation_reports = self._execute_automation_phase(nodes, action_plans)
        
        print(f"\n[ФАЗА 5] Генерирование итоговых отчётов...")
        final_reports = self._generate_final_reports(
            nodes, audit_reports, action_plans, automation_reports
        )
        
        self.reports = final_reports
        return final_reports
    
    def _prepare_target_nodes(
        self,
        ip_addresses: List[str],
        ssh_credentials: SSHCredentials,
        profile: str
    ) -> List[TargetNode]:
        nodes = []
        for ip in ip_addresses:
            node = TargetNode(
                ip_address=ip,
                ssh_credentials=ssh_credentials,
                profile=profile
            )
            nodes.append(node)
            print(f"  [OK] Подготовлен узел: {ip}")
        
        return nodes
    
    def _execute_audit_phase(self, nodes: List[TargetNode]) -> List[AuditReport]:
        audit_reports = []
        for node in nodes:
            print(f"  -> Аудит узла: {node.ip_address}")
            report = self.audit_module.audit_node_configuration(node, node.profile)
            audit_reports.append(report)
            print(f"    [OK] Завершено. Проверок: {len(report.checks)}")
        
        return audit_reports
    
    def _execute_decision_phase(
        self,
        audit_reports: List[AuditReport]
    ) -> List[Optional[CorrectiveActionPlan]]:
        action_plans = []
        for audit_report in audit_reports:
            print(f"  -> Анализ результатов для узла: {audit_report.node_ip}")
            plan = self.decision_engine.analyze_audit_results(audit_report)
            action_plans.append(plan)
            if plan:
                print(f"    [OK] План сформирован. Действий: {len(plan.actions)}")
            else:
                print(f"    [OK] Нарушений не обнаружено")
        
        return action_plans
    
    def _execute_automation_phase(
        self,
        nodes: List[TargetNode],
        action_plans: List[Optional[CorrectiveActionPlan]]
    ) -> List[Optional[AutomationExecutionReport]]:
        automation_reports = []
        
        for node, action_plan in zip(nodes, action_plans):
            if action_plan is None:
                automation_reports.append(None)
                continue
            
            print(f"  -> Выполнение плана для узла: {node.ip_address}")
            report = self.automation_manager.execute_action_plan(action_plan, node)
            automation_reports.append(report)
            
            status = "[OK] Успешно" if report.all_successful else "[ERROR] С ошибками"
            print(f"    {status}. Результатов: {len(report.results)}")
        
        return automation_reports
    
    # генерация итоговых отчетов
    def _generate_final_reports(
        self,
        nodes: List[TargetNode],
        audit_reports: List[AuditReport],
        action_plans: List[Optional[CorrectiveActionPlan]],
        automation_reports: List[Optional[AutomationExecutionReport]]
    ) -> List[MaturityAssessmentReport]:
        final_reports = []
        
        for i, node in enumerate(nodes):
            audit_report = audit_reports[i]
            action_plan = action_plans[i]
            automation_report = automation_reports[i]
            
            initial_level = self.decision_engine.assess_maturity_level(audit_report)
            
            updated_checks = []
            if automation_report and automation_report.all_successful:
                successful_action_ids = {result.action_id for result in automation_report.results if result.success}
                
                for check in audit_report.checks:
                    if check.compliant:
                        updated_checks.append(check)
                    else:
                        rule_key = self._check_to_correction.get(check.check_name)
                        if rule_key:
                            rule = CORRECTION_RULES.get(rule_key)
                            if rule:
                                action_ids = [action.get("id") for action in rule.get("actions", [])]
                                if any(action_id in successful_action_ids for action_id in action_ids):
                                    updated_check = AuditCheckResult(
                                        check_name=check.check_name,
                                        status=ServiceStatus.RUNNING,
                                        compliant=True,
                                        actual_value=check.expected_value,
                                        expected_value=check.expected_value,
                                        details=f"{check.details} (Исправлено автоматически)"
                                    )
                                    updated_checks.append(updated_check)
                                    continue
                        updated_checks.append(check)
            else:
                updated_checks = audit_report.checks
            
            updated_audit_report = AuditReport(
                node_ip=audit_report.node_ip,
                checks=updated_checks,
                timestamp=audit_report.timestamp,
                overall_status=audit_report.overall_status
            )
            
            final_level = self.decision_engine.assess_maturity_level(updated_audit_report)
            
            recommendations = self.decision_engine.generate_recommendations(updated_audit_report)
            
            report = MaturityAssessmentReport(
                node_ip=node.ip_address,
                timestamp=datetime.now().isoformat(),
                initial_maturity_level=initial_level,
                final_maturity_level=final_level,
                audit_report=updated_audit_report,
                original_audit_report=audit_report,
                correction_plan=action_plan,
                automation_report=automation_report,
                recommendations=recommendations
            )
            
            try:
                saved_id = self.save_report(report)
                print(f"Отчёт для узла {node.ip_address} сохранён в БД с ID: {saved_id}")
            except Exception as e:
                print(f"Ошибка сохранения отчёта для узла {node.ip_address}: {e}")
            
            final_reports.append(report)
        
        return final_reports
    
    def generate_user_report(
        self,
        assessment_report: MaturityAssessmentReport
    ) -> dict:
        original_non_compliant = [
            c for c in (assessment_report.original_audit_report.checks if assessment_report.original_audit_report else assessment_report.audit_report.checks)
            if not c.compliant
        ]
        
        issues_and_vulnerabilities = [
            {
                "check": check.check_name,
                "expected": str(check.expected_value),
                "actual": str(check.actual_value),
                "details": check.details
            }
            for check in original_non_compliant
        ]
        
        playbook_descriptions = {
            "playbooks/security/enable_https.yml": "Включает HTTPS на веб-серверах для защищенного соединения",
            "playbooks/security/harden_ssh.yml": "Усиливает безопасность SSH конфигурации",
            "playbooks/services/gitlab_security.yml": "Настраивает безопасность GitLab (HTTPS, CI/CD, security scanning)",
            "playbooks/services/redmine_security.yml": "Настраивает безопасность Redmine (workflow, issue tracking)",
            "playbooks/services/mattermost_security.yml": "Настраивает безопасность Mattermost (channels, integrations)"
        }
        
        corrections_made = []
        if assessment_report.automation_report:
            corrections_made = [
                {
                    "action": r.playbook,
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "idempotent": r.idempotent,
                    "details": playbook_descriptions.get(r.playbook, f"Выполняет действия по плейбуку {r.playbook}")
                }
                for r in assessment_report.automation_report.results
            ]
        
        correction_status = {
            "required": assessment_report.correction_plan is not None,
            "actions_planned": len(assessment_report.correction_plan.actions) if assessment_report.correction_plan else 0,
            "automation_executed": assessment_report.automation_report is not None,
            "automation_successful": assessment_report.automation_report.all_successful if assessment_report.automation_report else None
        }
        
        minimization_recommendations = assessment_report.recommendations
        if not minimization_recommendations:
            minimization_recommendations = [
                "Регулярно обновляйте сертификаты HTTPS для поддержания безопасного соединения",
                "Периодически проверяйте и обновляйте конфигурацию SSH для предотвращения уязвимостей",
                "Мониторьте логи системы для своевременного обнаружения потенциальных проблем"
            ]
        
        user_report = {
            "node_ip": assessment_report.node_ip,
            "timestamp": assessment_report.timestamp,
            "phase_1_findings": {
                "issues_and_vulnerabilities": issues_and_vulnerabilities,
                "maturity_level_before": assessment_report.initial_maturity_level.name
            },
            "phase_2_corrections": {
                "corrections_made": corrections_made,
                "correction_status": correction_status,
                "maturity_level_after": assessment_report.final_maturity_level.name
            },
            "phase_3_recommendations": {
                "minimization_recommendations": minimization_recommendations
            }
        }
        
        return user_report
    
    def export_report(
        self,
        assessment_report: MaturityAssessmentReport,
        format: str = "json"
    ) -> str:
        user_report = self.generate_user_report(assessment_report)
        
        if format.lower() == "json":
            return json.dumps(user_report, indent=2, ensure_ascii=False)
        
        elif format.lower() == "html":
            html_content = f"""
            <html>
                <head>
                    <title>Отчёт об оценке зрелости - {assessment_report.node_ip}</title>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h1 {{ color: #333; }}
                        h2 {{ color: #666; margin-top: 20px; }}
                        h3 {{ color: #888; margin-top: 15px; }}
                        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                        .passed {{ color: green; }}
                        .failed {{ color: red; }}
                        .phase {{ background-color: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                        .recommendations {{ background-color: #fff3cd; padding: 10px; border-radius: 5px; }}
                    </style>
                </head>
                <body>
                    <h1>Отчёт об оценке зрелости инфраструктуры</h1>
                    <p><strong>Узел:</strong> {assessment_report.node_ip}</p>
                    <p><strong>Дата:</strong> {assessment_report.timestamp}</p>
                    
                    <div class="phase">
                        <h2>1. Выявленные проблемы и уязвимости</h2>
                        <p><strong>Уровень зрелости до исправлений:</strong> {user_report['phase_1_findings']['maturity_level_before']}</p>
                        <h3>Проблемы и уязвимости:</h3>
                        <table>
                            <tr><th>Проверка</th><th>Ожидаемое</th><th>Фактическое</th><th>Детали</th></tr>
            """
            
            for item in user_report['phase_1_findings']['issues_and_vulnerabilities']:
                html_content += f"<tr><td>{item['check']}</td><td>{item['expected']}</td><td>{item['actual']}</td><td>{item['details']}</td></tr>"
            
            html_content += """
                        </table>
                    </div>
                    
                    <div class="phase">
                        <h2>2. Выполненные исправления</h2>
                        <p><strong>Уровень зрелости после исправлений:</strong> {user_report['phase_2_corrections']['maturity_level_after']}</p>
                        <h3>Статус исправлений:</h3>
                        <p>Требуются исправления: <strong>{"Да" if user_report['phase_2_corrections']['correction_status']['required'] else "Нет"}</strong></p>
                        <p>Запланировано действий: <strong>{user_report['phase_2_corrections']['correction_status']['actions_planned']}</strong></p>
                        <p>Автоматизация выполнена: <strong>{"Да" if user_report['phase_2_corrections']['correction_status']['automation_executed'] else "Нет"}</strong></p>
            """
            
            if user_report['phase_2_corrections']['correction_status']['automation_successful'] is not None:
                status_text = "Успешно" if user_report['phase_2_corrections']['correction_status']['automation_successful'] else "С ошибками"
                status_class = "passed" if user_report['phase_2_corrections']['correction_status']['automation_successful'] else "failed"
                html_content += f"<p>Статус автоматизации: <strong class='{status_class}'>{status_text}</strong></p>"
            
            html_content += """
                        <h3>Выполненные действия:</h3>
                        <table>
                            <tr><th>Действие</th><th>Описание</th><th>Успех</th><th>Время выполнения</th><th>Идемпотентно</th></tr>
            """
            
            for item in user_report['phase_2_corrections']['corrections_made']:
                success_text = "Да" if item['success'] else "Нет"
                success_class = "passed" if item['success'] else "failed"
                idempotent_text = "Да" if item['idempotent'] else "Нет"
                details = item.get('details', '')
                html_content += f"<tr><td>{item['action']}</td><td>{details}</td><td class='{success_class}'>{success_text}</td><td>{item['execution_time']:.2f}s</td><td>{idempotent_text}</td></tr>"
            
            html_content += """
                        </table>
                    </div>
                    
                    <div class="phase">
                        <h2>3. Рекомендации по минимизации проблем</h2>
                        <div class="recommendations">
                            <ul>
            """
            
            for rec in user_report['phase_3_recommendations']['minimization_recommendations']:
                html_content += f"<li>{rec}</li>"
            
            html_content += """
                            </ul>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            return html_content
        
        else:
            raise ValueError(f"Неподдерживаемый формат экспорта: {format}")

    def save_report(self, assessment_report: MaturityAssessmentReport) -> int:
        return self.database.save_report(assessment_report)

    def get_saved_reports(self) -> List[Dict[str, Any]]:
        return self.database.get_all_reports()

    def get_report_by_id(self, report_id: int) -> Optional[Dict[str, Any]]:
        return self.database.get_report_by_id(report_id)

    def get_reports_by_node(self, node_ip: str) -> List[Dict[str, Any]]:
        return self.database.get_reports_by_node(node_ip)
