import pytest
from unittest.mock import patch, Mock
from run_demo import check_devops_tools_configuration


class TestDemoRun:
    """Интеграционные тесты для демонстрационного запуска"""

    def test_check_devops_tools_configuration_with_defaults(self, capsys):
        """Тест проверки конфигурации DevOps инструментов с настройками по умолчанию"""
        with patch('run_demo.config_mod') as mock_config:
            # Мокаем конфиг с настройками по умолчанию
            mock_config.DEPLOYMENT_PARAMETERS = {
                "gitlab": {
                    "hostname": "gitlab.example.com",
                    "protocol": "http"
                },
                "redmine": {
                    "hostname": "redmine.example.com",
                    "protocol": "http"
                },
                "communication": {
                    "mattermost_hostname": "chat.example.com",
                    "protocol": "http"
                }
            }

            check_devops_tools_configuration()

            captured = capsys.readouterr()
            assert "[FAIL] GitLab:" in captured.out
            assert "[FAIL] Redmine:" in captured.out
            assert "[FAIL] Mattermost:" in captured.out

    def test_check_devops_tools_configuration_secure(self, capsys):
        """Тест проверки конфигурации DevOps инструментов с безопасными настройками"""
        with patch('run_demo.config_mod') as mock_config:
            # Мокаем конфиг с безопасными настройками
            mock_config.DEPLOYMENT_PARAMETERS = {
                "gitlab": {
                    "hostname": "gitlab.company.com",
                    "protocol": "https"
                },
                "redmine": {
                    "hostname": "redmine.company.com",
                    "protocol": "https"
                },
                "communication": {
                    "mattermost_hostname": "chat.company.com",
                    "protocol": "https"
                }
            }

            check_devops_tools_configuration()

            captured = capsys.readouterr()
            assert "[OK]" in captured.out and "GitLab:" in captured.out
            assert "[OK]" in captured.out and "Redmine:" in captured.out
            assert "[OK]" in captured.out and "Mattermost:" in captured.out