import pytest
from unittest.mock import patch, Mock
from app import MaturityAssessmentApplication
from models import SSHCredentials


class TestIntegration:
    """Интеграционные тесты"""

    @pytest.fixture
    def app(self):
        """Фикстура приложения"""
        return MaturityAssessmentApplication()

    @pytest.fixture
    def local_credentials(self):
        """Фикстура для локального SSH (для тестирования)"""
        return SSHCredentials(
            username="test",
            password="test",
            private_key_path=None
        )

    @patch('subprocess.run')
    def test_demo_run_with_mocked_ansible(self, mock_subprocess, app, local_credentials):
        """Демо тест с замоканным Ansible"""
        # Мокаем успешный запуск Ansible
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "PLAY RECAP ***\nlocalhost : ok=3 changed=1 unreachable=0 failed=0"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Мокаем аудит
        with patch.object(app.audit_module, 'audit_node_configuration') as mock_audit:
            mock_audit.return_value = Mock(
                node_ip="127.0.0.1",
                checks=[],
                timestamp="2024-01-01T00:00:00"
            )

            # Мокаем decision
            with patch.object(app.decision_engine, 'analyze_audit_results') as mock_decision:
                from models import CorrectiveActionPlan
                mock_decision.return_value = CorrectiveActionPlan(
                    node_ip="127.0.0.1",
                    actions=[]
                )

                # Запуск
                reports = app.initiate_maturity_assessment(
                    ip_addresses=["127.0.0.1"],
                    ssh_credentials=local_credentials,
                    profile="default"
                )

                assert len(reports) == 1
                assert reports[0].node_ip == "127.0.0.1"