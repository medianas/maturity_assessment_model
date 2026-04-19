import pytest
from models import SSHCredentials, TargetNode


@pytest.fixture
def sample_ssh_credentials():
    """Общая фикстура для SSH учетных данных"""
    return SSHCredentials(
        username="testuser",
        password="testpass123",
        private_key_path=None
    )


@pytest.fixture
def sample_target_node(sample_ssh_credentials):
    """Общая фикстура для целевого узла"""
    return TargetNode(
        ip_address="192.168.1.100",
        ssh_credentials=sample_ssh_credentials,
        profile="default"
    )


@pytest.fixture
def mock_ssh_connection():
    """Фикстура для мока SSH соединения"""
    class MockSSHConnection:
        def __init__(self):
            self.connected = False
            self.commands_executed = []

        def connect(self, hostname, username, password=None, key_filename=None, timeout=10):
            self.connected = True
            self.hostname = hostname
            self.username = username

        def exec_command(self, command):
            self.commands_executed.append(command)
            # Возвращаем мок объекты для stdin, stdout, stderr
            class MockChannel:
                def read(self):
                    return b"active\n"  # По умолчанию возвращаем успешный статус
                def close(self):
                    pass

            stdout = MockChannel()
            return None, stdout, None

        def close(self):
            self.connected = False

    return MockSSHConnection()