import pytest
from unittest.mock import Mock, patch
from app import MaturityAssessmentApplication
from models import SSHCredentials, TargetNode, AuditReport, AuditCheckResult, ServiceStatus
from config import AUDIT_PROFILES


class TestMaturityAssessmentApplication:
    """Тесты для основного приложения"""

    @pytest.fixture
    def app(self):
        """Фикстура приложения"""
        return MaturityAssessmentApplication()

    @pytest.fixture
    def valid_credentials(self):
        """Фикстура валидных SSH учетных данных"""
        return SSHCredentials(
            username="testuser",
            password="testpass",
            private_key_path=None
        )

    def test_validate_input_parameters_valid(self, app, valid_credentials):
        """Тест валидации корректных параметров"""
        result = app.validate_input_parameters(
            ip_addresses=["192.168.1.1"],
            ssh_credentials=valid_credentials,
            profile="default"
        )
        assert result is True

    def test_validate_input_parameters_no_ips(self, app, valid_credentials):
        """Тест валидации без IP адресов"""
        result = app.validate_input_parameters(
            ip_addresses=[],
            ssh_credentials=valid_credentials,
            profile="default"
        )
        assert result is False

    def test_validate_input_parameters_invalid_profile(self, app, valid_credentials):
        """Тест валидации с некорректным профилем"""
        result = app.validate_input_parameters(
            ip_addresses=["192.168.1.1"],
            ssh_credentials=valid_credentials,
            profile="invalid_profile"
        )
        assert result is False

    def test_validate_input_parameters_no_credentials(self, app):
        """Тест валидации без учетных данных"""
        credentials = SSHCredentials(username="", password="", private_key_path=None)
        result = app.validate_input_parameters(
            ip_addresses=["192.168.1.1"],
            ssh_credentials=credentials,
            profile="default"
        )
        assert result is False

    def test_initiate_maturity_assessment_success(self, app, valid_credentials):
        """Тест успешного выполнения полной оценки зрелости"""
        # Мокаем методы экземпляров
        with patch.object(app.audit_module, 'audit_node_configuration') as mock_audit_method:
            with patch.object(app.decision_engine, 'analyze_audit_results') as mock_decision_method:
                with patch.object(app.automation_manager, 'execute_action_plan') as mock_automation_method:
                    with patch.object(app.database, 'save_report') as mock_db_method:
                        # Настройка моков
                        mock_audit_method.return_value = AuditReport(
                            node_ip="192.168.1.1",
                            checks=[AuditCheckResult(
                                check_name="test_check",
                                status=ServiceStatus.RUNNING,
                                compliant=True,
                                actual_value="test",
                                expected_value="test",
                                details="Test check"
                            )],
                            timestamp="2024-01-01T00:00:00"
                        )

                        mock_decision_method.return_value = []
                        mock_automation_method.return_value = Mock(
                            all_successful=True,
                            results=[]
                        )
                        mock_db_method.return_value = None

                        # Выполнение теста
                        reports = app.initiate_maturity_assessment(
                            ip_addresses=["192.168.1.1"],
                            ssh_credentials=valid_credentials,
                            profile="default"
                        )

                        assert len(reports) == 1
                        assert reports[0].node_ip == "192.168.1.1"

    def test_prepare_target_nodes(self, app, valid_credentials):
        """Тест подготовки целевых узлов"""
        nodes = app._prepare_target_nodes(
            ip_addresses=["192.168.1.1", "192.168.1.2"],
            ssh_credentials=valid_credentials,
            profile="default"
        )

        assert len(nodes) == 2
        assert nodes[0].ip_address == "192.168.1.1"
        assert nodes[0].ssh_credentials.username == "testuser"
        assert nodes[0].profile == "default"

    def test_execute_audit_phase(self, app, valid_credentials):
        """Тест фазы аудита"""
        with patch.object(app.audit_module, 'audit_node_configuration') as mock_audit:
            mock_audit.return_value = AuditReport(
                node_ip="192.168.1.1",
                checks=[],
                timestamp="2024-01-01T00:00:00"
            )

            nodes = [
                TargetNode(
                    ip_address="192.168.1.1",
                    ssh_credentials=valid_credentials,
                    profile="default"
                )
            ]

            reports = app._execute_audit_phase(nodes)

            assert len(reports) == 1
            assert reports[0].node_ip == "192.168.1.1"
            mock_audit.assert_called_once()