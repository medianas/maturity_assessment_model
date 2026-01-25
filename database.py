
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any
from models import MaturityAssessmentReport

# Класс базы данных
class ReportDatabase:
    
    def __init__(self, db_path: str = "reports.db"):
        self.db_path = db_path
        self._init_db()

    # Инициализация схемы базы данных
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_ip TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    report_data TEXT NOT NULL,
                    created_at REAL
                )
            ''')
            conn.commit()

    # Сохранение отчета в базу данных
    def save_report(self, report: MaturityAssessmentReport) -> int:
        report_dict = {
            'node_ip': report.node_ip,
            'timestamp': report.timestamp,
            'initial_maturity_level': report.initial_maturity_level.value if report.initial_maturity_level else None,
            'final_maturity_level': report.final_maturity_level.value if report.final_maturity_level else None,
            'audit_report': {
                'node_ip': report.audit_report.node_ip,
                'timestamp': report.audit_report.timestamp,
                'checks': [
                    {
                        'check_name': check.check_name,
                        'status': check.status.value,
                        'compliant': check.compliant,
                        'actual_value': check.actual_value,
                        'expected_value': check.expected_value,
                        'details': check.details
                    } for check in report.audit_report.checks
                ],
                'overall_status': report.audit_report.overall_status.value
            },
            'correction_plan': {
                'node_ip': report.correction_plan.node_ip,
                'non_compliant_checks': [
                    {
                        'check_name': check.check_name,
                        'status': check.status.value,
                        'compliant': check.compliant,
                        'actual_value': check.actual_value,
                        'expected_value': check.expected_value,
                        'details': check.details
                    } for check in report.correction_plan.non_compliant_checks
                ] if report.correction_plan else [],
                'actions': [
                    {
                        'action_id': action.action_id,
                        'description': action.description,
                        'ansible_playbook': action.ansible_playbook,
                        'ansible_role': action.ansible_role,
                        'parameters': action.parameters,
                        'priority': action.priority
                    } for action in report.correction_plan.actions
                ] if report.correction_plan else [],
                'estimated_maturity_level': report.correction_plan.estimated_maturity_level.value if report.correction_plan and report.correction_plan.estimated_maturity_level else None
            } if report.correction_plan else None,
            'automation_report': {
                'node_ip': report.automation_report.node_ip,
                'timestamp': report.automation_report.timestamp,
                'results': [
                    {
                        'action_id': result.action_id,
                        'success': result.success,
                        'execution_time': result.execution_time,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'idempotent': result.idempotent
                    } for result in report.automation_report.results
                ],
                'all_successful': report.automation_report.all_successful
            } if report.automation_report else None,
            'recommendations': report.recommendations
        }

        report_json = json.dumps(report_dict, ensure_ascii=False, indent=2)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO reports (node_ip, timestamp, report_data, created_at)
                VALUES (?, ?, ?, ?)
            ''', (report.node_ip, report.timestamp, report_json, datetime.now().timestamp()))
            conn.commit()
            return cursor.lastrowid

    def get_all_reports(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, node_ip, timestamp, created_at
                FROM reports
                ORDER BY created_at DESC
            ''')
            return [
                {
                    'id': row[0],
                    'node_ip': row[1],
                    'timestamp': row[2],
                    'created_at': datetime.fromtimestamp(row[3]).isoformat()
                }
                for row in cursor.fetchall()
            ]

    def get_report_by_id(self, report_id: int) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, node_ip, timestamp, report_data, created_at
                FROM reports
                WHERE id = ?
            ''', (report_id,))
            row = cursor.fetchone()

            if row:
                return {
                    'id': row[0],
                    'node_ip': row[1],
                    'timestamp': row[2],
                    'report_data': json.loads(row[3]),
                    'created_at': datetime.fromtimestamp(row[4]).isoformat()
                }
            return None

    def get_reports_by_node(self, node_ip: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, node_ip, timestamp, created_at
                FROM reports
                WHERE node_ip = ?
                ORDER BY created_at DESC
            ''', (node_ip,))
            return [
                {
                    'id': row[0],
                    'node_ip': row[1],
                    'timestamp': row[2],
                    'created_at': datetime.fromtimestamp(row[3]).isoformat()
                }
                for row in cursor.fetchall()
            ]