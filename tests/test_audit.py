import pytest
from unittest.mock import Mock, patch, MagicMock
import socket
from audit import InfrastructureAudit
from models import TargetNode, SSHCredentials, AuditCheckResult, ServiceStatus


class TestInfrastructureAudit:
    """Тесты для модуля аудита"""

    @pytest.fixture
    def audit(self):
        """Фикстура аудита"""
        return InfrastructureAudit()

    @pytest.fixture
    def test_node(self):
        """Фикстура тестового узла"""
        return TargetNode(
            ip_address="192.168.1.1",
            ssh_credentials=SSHCredentials(
                username="testuser",
                password="testpass",
                private_key_path=None
            ),
            profile="default"
        )

    def test_audit_node_configuration(self, audit, test_node):
        """Тест аудита конфигурации узла"""
        with patch.object(audit, '_run_check') as mock_run_check:
            mock_run_check.return_value = AuditCheckResult(
                check_name="test_check",
                status=ServiceStatus.RUNNING,
                compliant=True,
                actual_value="test",
                expected_value="test",
                details="Test"
            )

            report = audit.audit_node_configuration(test_node, "default")

            assert report.node_ip == "192.168.1.1"
            assert len(report.checks) > 0

    @patch('audit.socket.socket')
    def test_check_port_open_success(self, mock_socket, audit):
        """Тест успешной проверки открытого порта"""
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        mock_sock.connect_ex.return_value = 0  # Успешное подключение

        result = audit._check_port_open("192.168.1.1", 80)

        assert result is True
        mock_sock.connect_ex.assert_called_once_with(("192.168.1.1", 80))
        mock_sock.close.assert_called_once()

    @patch('audit.socket.socket')
    def test_check_port_open_failure(self, mock_socket, audit):
        """Тест неудачной проверки открытого порта"""
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        mock_sock.connect_ex.return_value = 1  # Неудачное подключение

        result = audit._check_port_open("192.168.1.1", 80)

        assert result is False

    @patch('audit.socket.socket')
    def test_check_port_open_exception(self, mock_socket, audit):
        """Тест проверки порта с исключением"""
        mock_socket.side_effect = Exception("Network error")

        result = audit._check_port_open("192.168.1.1", 80)

        assert result is False

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_service_availability_with_services(self, mock_check_port, audit, test_node):
        """Тест проверки доступности сервисов с доступными сервисами"""
        mock_check_port.side_effect = [True, True, True]  # HTTP, HTTPS, SSH доступны

        result = audit._check_service_availability(test_node)

        assert result.compliant is True
        assert result.status == ServiceStatus.RUNNING
        assert "HTTP(80)" in result.actual_value
        assert "HTTPS(443)" in result.actual_value
        assert "SSH(22)" in result.actual_value

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_service_availability_no_services(self, mock_check_port, audit, test_node):
        """Тест проверки доступности сервисов без доступных сервисов"""
        mock_check_port.return_value = False

        result = audit._check_service_availability(test_node)

        assert result.compliant is False
        assert result.status == ServiceStatus.STOPPED
        assert result.actual_value == "none"

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_https_enabled_https_available(self, mock_check_port, audit, test_node):
        """Тест проверки HTTPS когда HTTPS доступен"""
        mock_check_port.side_effect = [True, False]  # HTTPS есть, HTTP нет

        result = audit._check_https_enabled(test_node)

        assert result.compliant is True
        assert result.actual_value == "HTTPS enabled"
        assert "HTTPS доступен" in result.details

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_https_enabled_http_only(self, mock_check_port, audit, test_node):
        """Тест проверки HTTPS когда только HTTP доступен"""
        mock_check_port.side_effect = [False, True]  # HTTPS нет, HTTP есть

        result = audit._check_https_enabled(test_node)

        assert result.compliant is False
        assert result.actual_value == "HTTP only"
        assert "Только HTTP доступен" in result.details

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_https_enabled_no_web_service(self, mock_check_port, audit, test_node):
        """Тест проверки HTTPS когда веб-сервисы недоступны"""
        mock_check_port.return_value = False

        result = audit._check_https_enabled(test_node)

        assert result.compliant is False
        assert result.actual_value == "No web service"
        assert "Веб-сервисы недоступны" in result.details

    @patch('audit.paramiko.SSHClient')
    def test_check_ssh_config_success(self, mock_ssh_client, audit, test_node):
        """Тест успешной проверки SSH конфигурации"""
        mock_ssh = Mock()
        mock_ssh_client.return_value = mock_ssh

        # Мокаем stdout для команды grep
        mock_stdout = Mock()
        mock_stdout.read.return_value = b"PermitRootLogin no\nPasswordAuthentication no\n"
        mock_ssh.exec_command.return_value = (None, mock_stdout, None)

        result = audit._check_ssh_config(test_node)

        assert result.compliant is True
        assert "RootLogin:no" in result.actual_value
        assert "PasswordAuth:no" in result.actual_value
        mock_ssh.connect.assert_called_once()
        mock_ssh.exec_command.assert_called_once()
        mock_ssh.close.assert_called_once()

    @patch('audit.paramiko.SSHClient')
    def test_check_ssh_config_weak(self, mock_ssh_client, audit, test_node):
        """Тест проверки SSH конфигурации с уязвимостями"""
        mock_ssh = Mock()
        mock_ssh_client.return_value = mock_ssh

        # Мокаем stdout с уязвимой конфигурацией
        mock_stdout = Mock()
        mock_stdout.read.return_value = b"PermitRootLogin yes\nPasswordAuthentication yes\n"
        mock_ssh.exec_command.return_value = (None, mock_stdout, None)

        result = audit._check_ssh_config(test_node)

        assert result.compliant is False
        assert "RootLogin:yes" in result.actual_value
        assert "PasswordAuth:yes" in result.actual_value

    @patch('audit.paramiko.SSHClient')
    def test_check_ssh_config_connection_error(self, mock_ssh_client, audit, test_node):
        """Тест проверки SSH конфигурации с ошибкой подключения"""
        mock_ssh_client.side_effect = Exception("Connection failed")

        result = audit._check_ssh_config(test_node)

        assert result.compliant is False
        assert result.status == ServiceStatus.ERROR
        assert "SSH connection failed" in result.actual_value

    @patch('audit.paramiko.SSHClient')
    def test_check_firewall_active(self, mock_ssh_client, audit, test_node):
        """Тест проверки firewall когда он активен"""
        mock_ssh = Mock()
        mock_ssh_client.return_value = mock_ssh

        mock_stdout = Mock()
        mock_stdout.read.return_value = b"active\n"
        mock_ssh.exec_command.return_value = (None, mock_stdout, None)

        result = audit._check_firewall(test_node)

        assert result.compliant is True
        assert result.actual_value == "active"
        assert "Firewall активен" in result.details

    @patch('audit.paramiko.SSHClient')
    def test_check_firewall_inactive(self, mock_ssh_client, audit, test_node):
        """Тест проверки firewall когда он неактивен"""
        mock_ssh = Mock()
        mock_ssh_client.return_value = mock_ssh

        mock_stdout = Mock()
        mock_stdout.read.return_value = b"inactive\n"
        mock_ssh.exec_command.return_value = (None, mock_stdout, None)

        result = audit._check_firewall(test_node)

        assert result.compliant is False
        assert result.actual_value == "inactive"

    @patch('audit.paramiko.SSHClient')
    def test_check_firewall_not_installed(self, mock_ssh_client, audit, test_node):
        """Тест проверки firewall когда он не установлен"""
        mock_ssh = Mock()
        mock_ssh_client.return_value = mock_ssh

        mock_stdout = Mock()
        mock_stdout.read.return_value = b"no_firewall\n"
        mock_ssh.exec_command.return_value = (None, mock_stdout, None)

        result = audit._check_firewall(test_node)

        assert result.compliant is False
        assert result.actual_value == "not_installed"

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_connectivity_reachable(self, mock_check_port, audit, test_node):
        """Тест проверки connectivity когда узел доступен"""
        mock_check_port.return_value = True

        result = audit._check_connectivity(test_node)

        assert result.compliant is True
        assert result.status == ServiceStatus.RUNNING
        assert result.actual_value == "reachable"

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_connectivity_unreachable(self, mock_check_port, audit, test_node):
        """Тест проверки connectivity когда узел недоступен"""
        mock_check_port.return_value = False

        result = audit._check_connectivity(test_node)

        assert result.compliant is False
        assert result.status == ServiceStatus.STOPPED
        assert result.actual_value == "unreachable"

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_gitlab_integration_available_https(self, mock_check_port, audit, test_node):
        """Тест проверки GitLab интеграции с HTTPS"""
        # any([80,443,8080]): 80=False, 443=True → stop; then https_available(443)=True
        mock_check_port.side_effect = [False, True, True]

        result = audit._check_gitlab_integration(test_node)

        assert result.compliant is True
        assert result.status == ServiceStatus.RUNNING
        assert result.actual_value == "available_with_https"

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_gitlab_integration_http_only(self, mock_check_port, audit, test_node):
        """Тест проверки GitLab интеграции только с HTTP"""
        mock_check_port.side_effect = [True, False, False]  # HTTP есть, HTTPS нет

        result = audit._check_gitlab_integration(test_node)

        assert result.compliant is False
        assert result.actual_value == "available_http_only"

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_gitlab_integration_not_available(self, mock_check_port, audit, test_node):
        """Тест проверки GitLab интеграции когда сервис недоступен"""
        mock_check_port.return_value = False

        result = audit._check_gitlab_integration(test_node)

        assert result.compliant is False
        assert result.status == ServiceStatus.STOPPED
        assert result.actual_value == "not_available"

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_redmine_integration_available_https(self, mock_check_port, audit, test_node):
        """Тест проверки Redmine интеграции с HTTPS"""
        # any([80,443,3000]): 80=False, 443=True → stop; then https_available(443)=True
        mock_check_port.side_effect = [False, True, True]

        result = audit._check_redmine_integration(test_node)

        assert result.compliant is True
        assert result.status == ServiceStatus.RUNNING
        assert result.actual_value == "available_with_https"

    @patch.object(InfrastructureAudit, '_check_port_open')
    def test_check_mattermost_integration_available_https(self, mock_check_port, audit, test_node):
        """Тест проверки Mattermost интеграции с HTTPS"""
        # any([80,443,8065]): 80=False, 443=True → stop; then https_available(443)=True
        mock_check_port.side_effect = [False, True, True]

        result = audit._check_mattermost_integration(test_node)

        assert result.compliant is True
        assert result.status == ServiceStatus.RUNNING
        assert result.actual_value == "available_with_https"