
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class MaturityLevel(Enum):
    CRITICAL = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    OPTIMAL = 5

# Определение перечисления статуса сервиса
class ServiceStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"

# Класс данных учетных данных SSH
@dataclass
class SSHCredentials:
    username: str
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    port: int = 22

# Класс данных целевого узла
@dataclass
class TargetNode:
    ip_address: str
    ssh_credentials: SSHCredentials
    profile: str = "default"

# Класс данных результата проверки аудита
@dataclass
class AuditCheckResult:
    check_name: str
    status: ServiceStatus
    expected_value: Any
    actual_value: Any
    compliant: bool
    details: str = ""

# Класс данных отчета аудита
@dataclass
class AuditReport:
    node_ip: str
    timestamp: str
    checks: List[AuditCheckResult] = field(default_factory=list)
    overall_status: ServiceStatus = ServiceStatus.UNKNOWN

# Класс данных действия коррекции
@dataclass
class CorrectionAction:
    action_id: str
    description: str
    ansible_playbook: str
    ansible_role: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1

# Класс данных плана корректирующих действий
@dataclass
class CorrectiveActionPlan:
    node_ip: str
    non_compliant_checks: List[AuditCheckResult] = field(default_factory=list)
    actions: List[CorrectionAction] = field(default_factory=list)
    estimated_maturity_level: MaturityLevel = MaturityLevel.CRITICAL

# Класс данных результата выполнения автоматизации
@dataclass
class AutomationExecutionResult:
    action_id: str
    success: bool
    execution_time: float
    stdout: str = ""
    stderr: str = ""
    idempotent: bool = True
    playbook: str = ""

# Класс данных отчета выполнения автоматизации
@dataclass
class AutomationExecutionReport:
    node_ip: str
    timestamp: str
    results: List[AutomationExecutionResult] = field(default_factory=list)
    all_successful: bool = True

# Класс данных отчета оценки зрелости
@dataclass
class MaturityAssessmentReport:
    node_ip: str
    timestamp: str
    initial_maturity_level: MaturityLevel
    final_maturity_level: MaturityLevel
    audit_report: AuditReport
    original_audit_report: Optional[AuditReport] = None
    correction_plan: Optional[CorrectiveActionPlan] = None
    automation_report: Optional[AutomationExecutionReport] = None
    recommendations: List[str] = field(default_factory=list)
