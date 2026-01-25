from typing import List, Optional, Dict, Any
from models import (
    AuditReport,
    CorrectiveActionPlan,
    CorrectionAction,
    MaturityLevel,
    MaturityAssessmentReport,
    AuditCheckResult
)


# основной класс
class DecisionEngine:
    
    # инициализация движка решений
    def __init__(self):
        self._rules = {}
        self._load_rules()
    
    # загрузка правил коррекции из конфига
    def _load_rules(self) -> None:
        from config import CORRECTION_RULES
        self._rules = CORRECTION_RULES
    
    # анализ результатов аудита и формирование плана
    def analyze_audit_results(self, audit_report: AuditReport) -> Optional[CorrectiveActionPlan]:
        non_compliant_checks = self._identify_non_compliant_checks(audit_report)
        
        if not non_compliant_checks:
            return None
        
        correction_actions = self._generate_correction_actions(non_compliant_checks)
        
        estimated_level = self.assess_maturity_level(audit_report)
        
        action_plan = CorrectiveActionPlan(
            node_ip=audit_report.node_ip,
            non_compliant_checks=non_compliant_checks,
            actions=correction_actions,
            estimated_maturity_level=estimated_level
        )
        
        return action_plan
    
    # Выявление несоответствующих проверок
    def _identify_non_compliant_checks(self, audit_report: AuditReport) -> List[AuditCheckResult]:
        return [check for check in audit_report.checks if not check.compliant]
    
    def _generate_correction_actions(self, non_compliant_checks: List[AuditCheckResult]) -> List[CorrectionAction]:
        actions = []
        
        for check in non_compliant_checks:
            rule_key = None
            
            check_to_rule_map = {
                "https_enabled": "https_not_enabled",
                "ssh_config": "insecure_ssh_config",
                "encryption_algorithms": "weak_encryption",
                "security_updates": "missing_security_updates",
                "firewall_status": "firewall_misconfigured",
                "gitlab_integration": "gitlab_not_secure",
                "redmine_integration": "redmine_not_secure",
                "mattermost_integration": "mattermost_not_secure"
            }
            
            rule_key = check_to_rule_map.get(check.check_name)
            
            if rule_key and rule_key in self._rules:
                rule = self._rules[rule_key]
                
                for action_config in rule.get("actions", []):
                    action = CorrectionAction(
                        action_id=action_config.get("id"),
                        description=action_config.get("description"),
                        ansible_playbook=action_config.get("playbook", ""),
                        ansible_role=action_config.get("role"),
                        parameters={"check_name": check.check_name},
                        priority=action_config.get("priority", 2)
                    )
                    actions.append(action)
        
        actions.sort(key=lambda a: a.priority)
        
        return actions
    
    # оценка уровня зрелости инфраструктуры
    def assess_maturity_level(self, audit_report: AuditReport) -> MaturityLevel:
        criterion_levels = self._assess_maturity_criteria(audit_report)
        
        level_counts = {}
        for level in criterion_levels.values():
            level_counts[level] = level_counts.get(level, 0) + 1
        
        max_count = max(level_counts.values())
        candidate_levels = [lvl for lvl, count in level_counts.items() if count == max_count]
        final_level = min(candidate_levels)
        
        return MaturityLevel(final_level)
    
    # оценка критериев зрелости по шкале
    def _assess_maturity_criteria(self, audit_report: AuditReport) -> Dict[str, int]:
        criteria = {}
        
        check_results = {check.check_name: check for check in audit_report.checks}
        
        gitlab = check_results.get('gitlab_integration')
        connectivity = check_results.get('connectivity')
        if gitlab and gitlab.compliant and connectivity and connectivity.compliant:
            criteria['infrastructure_reproducibility'] = 4
        elif gitlab and gitlab.compliant:
            criteria['infrastructure_reproducibility'] = 3
        elif connectivity and connectivity.compliant:
            criteria['infrastructure_reproducibility'] = 2
        else:
            criteria['infrastructure_reproducibility'] = 1
        
        if gitlab and gitlab.compliant:
            criteria['automated_deployment'] = 4
        else:
            criteria['automated_deployment'] = 1
        
        security_checks = ['https_enabled', 'ssh_config', 'firewall_status']
        security_compliant = sum(1 for check in security_checks if check_results.get(check) and check_results[check].compliant)
        if security_compliant == len(security_checks) and gitlab and gitlab.compliant:
            criteria['security_shift_left'] = 4
        elif security_compliant >= 2:
            criteria['security_shift_left'] = 3
        elif security_compliant >= 1:
            criteria['security_shift_left'] = 2
        else:
            criteria['security_shift_left'] = 1
        
        baseline_checks = ['https_enabled', 'ssh_config', 'firewall_status']
        baseline_compliant = sum(1 for check in baseline_checks if check_results.get(check) and check_results[check].compliant)
        if baseline_compliant == len(baseline_checks):
            criteria['baseline_configurations'] = 4
        elif baseline_compliant >= 2:
            criteria['baseline_configurations'] = 3
        elif baseline_compliant >= 1:
            criteria['baseline_configurations'] = 2
        else:
            criteria['baseline_configurations'] = 1
        
        criteria['automated_remediation'] = 3
        
        integration_checks = ['gitlab_integration', 'redmine_integration', 'mattermost_integration']
        integration_compliant = sum(1 for check in integration_checks if check_results.get(check) and check_results[check].compliant)
        if integration_compliant == len(integration_checks):
            criteria['tool_integration'] = 4
        elif integration_compliant >= 2:
            criteria['tool_integration'] = 3
        elif integration_compliant >= 1:
            criteria['tool_integration'] = 2
        else:
            criteria['tool_integration'] = 1
        
        criteria['transparency'] = 4
        
        criteria['policies_in_code'] = 4
        
        if gitlab and gitlab.compliant:
            criteria['change_management'] = 3
        else:
            criteria['change_management'] = 2
        
        criteria['scalability_practices'] = 3
        
        return criteria
    
    def _calculate_compliance_score(self, audit_report: AuditReport) -> float:
        if not audit_report.checks:
            return 0.0
        
        passed_checks = len([c for c in audit_report.checks if c.compliant])
        total_checks = len(audit_report.checks)
        
        return passed_checks / total_checks if total_checks > 0 else 0.0
    
    # Генерация списка рекомендаций
    def generate_recommendations(self, audit_report: AuditReport) -> List[str]:
        recommendations = []
        maturity_level = self.assess_maturity_level(audit_report)
        
        from config import MATURITY_RECOMMENDATIONS
        
        if maturity_level in MATURITY_RECOMMENDATIONS:
            recommendations = MATURITY_RECOMMENDATIONS[maturity_level]
        
        for check in audit_report.checks:
            if not check.compliant:
                if "https" in check.check_name.lower():
                    recommendations.append(f"Требуется срочно включить HTTPS: {check.details}")
                elif "ssh" in check.check_name.lower():
                    recommendations.append(f"Требуется усилить SSH конфигурацию: {check.details}")
                elif "security" in check.check_name.lower():
                    recommendations.append(f"Требуется применить обновления безопасности: {check.details}")
        
        return recommendations
