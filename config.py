# Правила коррекции для связывания несоответствий с корректирующими действиями
CORRECTION_RULES = {
    "https_not_enabled": {
        "description": "HTTPS не включён",
        "actions": [
            {
                "id": "enable_https",
                "description": "Включить HTTPS",
                "playbook": "playbooks/security/enable_https.yml",
                "priority": 1
            }
        ],
        "severity": "HIGH"
    },
    "insecure_ssh_config": {
        "description": "Небезопасная конфигурация SSH",
        "actions": [
            {
                "id": "harden_ssh",
                "description": "Усилить безопасность SSH",
                "playbook": "playbooks/security/harden_ssh.yml",
                "role": "security/ssh_hardening",
                "priority": 1
            }
        ],
        "severity": "CRITICAL"
    },
    "weak_encryption": {
        "description": "Слабое шифрование",
        "actions": [
            {
                "id": "upgrade_encryption",
                "description": "Обновить алгоритмы шифрования",
                "playbook": "playbooks/security/upgrade_encryption.yml",
                "priority": 2
            }
        ],
        "severity": "HIGH"
    },
    "missing_security_updates": {
        "description": "Отсутствуют безопасности обновления",
        "actions": [
            {
                "id": "apply_security_updates",
                "description": "Применить безопасности обновления",
                "playbook": "playbooks/maintenance/security_updates.yml",
                "priority": 1
            }
        ],
        "severity": "HIGH"
    },
    "firewall_misconfigured": {
        "description": "Неправильная конфигурация брандмауэра",
        "actions": [
            {
                "id": "configure_firewall",
                "description": "Настроить брандмауэр согласно профилю",
                "playbook": "playbooks/networking/configure_firewall.yml",
                "priority": 2
            }
        ],
        "severity": "MEDIUM"
    },
    "gitlab_not_secure": {
        "description": "GitLab не настроен безопасно",
        "actions": [
            {
                "id": "secure_gitlab",
                "description": "Настроить безопасность GitLab",
                "playbook": "playbooks/services/gitlab_security.yml",
                "role": "services/gitlab_hardening",
                "priority": 2
            }
        ],
        "severity": "HIGH"
    },
    "redmine_not_secure": {
        "description": "Redmine не настроен безопасно",
        "actions": [
            {
                "id": "secure_redmine",
                "description": "Настроить безопасность Redmine",
                "playbook": "playbooks/services/redmine_security.yml",
                "role": "services/redmine_hardening",
                "priority": 2
            }
        ],
        "severity": "HIGH"
    },
    "mattermost_not_secure": {
        "description": "Mattermost не настроен безопасно",
        "actions": [
            {
                "id": "secure_mattermost",
                "description": "Настроить безопасность Mattermost",
                "playbook": "playbooks/services/mattermost_security.yml",
                "role": "services/mattermost_hardening",
                "priority": 2
            }
        ],
        "severity": "HIGH"
    }
}

# Профили аудита с наборами проверяемых параметров
AUDIT_PROFILES = {
    "default": {
        "checks": [
            "service_availability",
            "https_enabled",
            "ssh_config",
            "firewall_status"
        ]
    },
    "admin": {
        "checks": [
            "service_availability",
            "https_enabled",
            "ssh_config",
            "firewall_status",
            "gitlab_integration",
            "redmine_integration",
            "mattermost_integration"
        ]
    },
    "user": {
        "checks": [
            "service_availability",
            "connectivity"
        ]
    }
}

# Рекомендуемые действия по уровню зрелости
MATURITY_RECOMMENDATIONS = {
    1: [
        "Критическое состояние: внедрите базовую повторяемость инфраструктуры через IaC для ключевых компонентов",
        "Перейдите от ручного развертывания к частичной автоматизации с CI/CD без security",
        "Внедрите реактивную безопасность: начните с отдельных мер hardening",
        "Определите частичные эталонные конфигурации безопасности (HTTPS, SSH)",
        "Организуйте ручную реакцию на несоответствия с документированными процедурами",
        "Свяжите инструменты жизненного цикла частично (GitLab-Redmine интеграция)",
        "Внедрите ограниченную прозрачность: базовое логирование и мониторинг",
        "Отсутствуют политики в коде: начните с ручного контроля конфигураций",
        "Неконтролируемые изменения: внедрите ручную фиксацию изменений",
        "Не масштабируются практики: подготовьте частичные шаблоны для расширения"
    ],
    2: [
        "Низкий уровень: расширьте IaC на все компоненты для полной повторяемости",
        "Внедрите CI/CD для основных сервисов с частичной автоматизацией",
        "Перейдите к разовым проверкам безопасности на отдельных этапах",
        "Заданы частично эталонные конфигурации: определите baseline для всех сервисов",
        "Организуйте ручную реакцию на несоответствия",
        "Обеспечьте частичную связанность инструментов жизненного цикла",
        "Расширьте прозрачность до централизованного логирования",
        "Ручной контроль: внедрите частичный Policy-as-Code для ключевых политик",
        "Ручная фиксация изменений: внедрите версионирование инфраструктуры",
        "Частичные шаблоны: разработайте типовые модули для повторного использования"
    ],
    3: [
        "Средний уровень: добавьте self-service возможности для полной IaC",
        "Полностью автоматизируйте развертывание с CI/CD для всех сервисов",
        "Внедрите security scanning на этапах CI для shift-left подхода",
        "Определены baseline: применяйте автопроверку эталонных конфигураций",
        "Организуйте полуавтоматическую реакцию на несоответствия",
        "Обеспечьте сквозную интеграцию инструментов жизненного цикла",
        "Перейдите к полной наблюдаемости процессов с централизованным мониторингом",
        "Частичный Policy-as-Code: внедрите полный Policy-as-Code для всех политик",
        "Версионирование: добавьте автоматический rollback при изменениях",
        "Типовые модули: разработайте универсальные шаблоны для разных проектов"
    ],
    4: [
        "Высокий уровень: оптимизируйте self-service IaC для максимальной эффективности",
        "Поддерживайте полный CI/CD с автоматизированным развертыванием без ручных операций",
        "Углубите интеграцию безопасности с security-gates в CI/CD",
        "Автопроверка baseline: внедрите непрерывный compliance контроль",
        "Обеспечьте автоматическую реакцию на несоответствия",
        "Добавьте event-driven интеграцию инструментов жизненного цикла",
        "Поддерживайте полную observability с аналитическими возможностями",
        "Полный Policy-as-Code: внедрите динамические политики с автоматической адаптацией",
        "Автоматический rollback: обеспечьте самокоррекцию при изменениях",
        "Универсальные шаблоны: внедрите платформенный подход к инфраструктуре"
    ],
    5: [
        "Оптимальный уровень: поддерживайте self-service IaC с инновациями",
        "Совершенствуйте полностью автоматизированное развертывание с новыми технологиями",
        "Поддерживайте security-by-design с передовыми практиками",
        "Обеспечивайте непрерывный compliance с самообучением",
        "Поддерживайте автономную реакцию на несоответствия с предиктивными мерами",
        "Оптимизируйте event-driven интеграцию с AI/ML",
        "Расширяйте аналитическую прозрачность с автоматизированным принятием решений",
        "Поддерживайте динамические политики с машинным обучением",
        "Обеспечивайте самокоррекцию с прогнозированием трендов",
        "Поддерживайте платформенный подход с автоматической эволюцией"
    ]
}

# Параметры развертывания и интеграции
DEPLOYMENT_PARAMETERS = {
    "gitlab": {
        "hostname": "gitlab.example.com",
        "port": 443,
        "protocol": "https",
        "docker_port": 8080,
        "registry_port": 5005,
        "ssh_port": 2222
    },
    "redmine": {
        "hostname": "redmine.example.com",
        "port": 443,
        "protocol": "https",
        "docker_port": 3000
    },
    "communication": {
        "mattermost_hostname": "chat.example.com",
        "mattermost_port": 443,
        "protocol": "https",
        "mattermost_docker_port": 8065
    }
}

# Параметры интеграции для вебхуков, токенов, API
INTEGRATION_PARAMETERS = {
    "gitlab_redmine_webhook": {
        "description": "Webhook для синхронизации GitLab-Redmine",
        "event_types": ["push", "issue", "merge_request"],
        "requires_auth": True,
        "auth_type": "token"
    },
    "gitlab_mattermost_webhook": {
        "description": "Webhook для уведомлений в Mattermost",
        "event_types": ["push", "issue", "pipeline"],
        "requires_auth": True,
        "auth_type": "token"
    },
    "redmine_api": {
        "description": "API для интеграции с Redmine",
        "version": "v3",
        "requires_auth": True,
        "auth_type": "api_key"
    }
}

# Инвентарь узлов и групп хостов
ANSIBLE_INVENTORY = {
    "all": {
        "hosts": {},
        "vars": {
            "ansible_user": "root",
            "ansible_ssh_port": 22,
            "ansible_connection": "ssh"
        }
    },
    "gitlab": {
        "hosts": ["192.168.1.100"],
        "vars": {
            "gitlab_hostname": "gitlab.example.com",
            "gitlab_port": 443,
            "gitlab_admin_email": "admin@example.com"
        }
    },
    "redmine": {
        "hosts": ["192.168.1.101"],
        "vars": {
            "redmine_hostname": "redmine.example.com",
            "redmine_port": 443,
            "redmine_db_host": "192.168.1.102",
            "redmine_db_user": "redmine"
        }
    },
    "communication": {
        "hosts": ["192.168.1.103"],
        "vars": {
            "mattermost_hostname": "chat.example.com",
            "mattermost_port": 443
        }
    },
    "docker_hosts": {
        "hosts": ["192.168.1.100", "192.168.1.101", "192.168.1.103"],
        "vars": {
            "docker_version": "20.10.12"
        }
    }
}

# Переменные развертывания для Docker Compose и IaC
DOCKER_COMPOSE_VARIABLES = {
    "gitlab": {
        "image": "gitlab/gitlab-ce:latest",
        "environment": {
            "GITLAB_OMNIBUS_CONFIG": "external_url 'https://gitlab.example.com'",
            "GITLAB_ROOT_PASSWORD": "{{ gitlab_root_password }}",
            "GITLAB_SHARED_RUNNERS_REGISTRATION_TOKEN": "{{ gitlab_runner_token }}"
        },
        "volumes": {
            "gitlab_config": "/etc/gitlab",
            "gitlab_logs": "/var/log/gitlab",
            "gitlab_data": "/var/opt/gitlab"
        },
        "networks": ["backend"]
    },
    "redmine": {
        "image": "redmine:latest",
        "environment": {
            "REDMINE_DB_MYSQL": "redmine_db",
            "REDMINE_DB_USERNAME": "redmine",
            "REDMINE_DB_PASSWORD": "{{ redmine_db_password }}",
            "REDMINE_DB_DATABASE": "redmine"
        },
        "volumes": {
            "redmine_data": "/usr/src/redmine/files"
        },
        "networks": ["backend"],
        "depends_on": ["redmine_db"]
    },
    "mattermost": {
        "image": "mattermost/mattermost-team-edition:latest",
        "environment": {
            "MM_SQLSETTINGS_DATASOURCE": "postgres://mattermost:{{ mattermost_db_password }}@mattermost_db/mattermost",
            "MM_SERVICESETTINGS_SITEURL": "https://chat.example.com",
            "MM_SERVICESETTINGS_ENABLESSL": "true"
        },
        "volumes": {
            "mattermost_config": "/mattermost/config",
            "mattermost_data": "/mattermost/data"
        },
        "networks": ["backend"],
        "depends_on": ["mattermost_db"]
    }
}

# Параметры безопасности и доступа
SECURITY_PARAMETERS = {
    "ssh": {
        "port": 2222,
        "permit_root_login": False,
        "password_authentication": False,
        "pubkey_authentication": True,
        "key_file_permissions": "0600"
    },
    "https": {
        "min_tls_version": "1.2",
        "ciphers": "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384",
        "certificate_path": "/etc/ssl/certs/{{ hostname }}.crt",
        "key_path": "/etc/ssl/private/{{ hostname }}.key"
    },
    "firewall": {
        "default_policy_incoming": "DROP",
        "default_policy_outgoing": "ACCEPT",
        "allowed_ports": [22, 2222, 80, 443, 8080, 8065, 5005]
    }
}

# Пути и конфигурация плейбуков
PLAYBOOK_PATHS = {
    "enable_https": "playbooks/security/enable_https.yml",
    "harden_ssh": "playbooks/security/harden_ssh.yml",
    "upgrade_encryption": "playbooks/security/upgrade_encryption.yml",
    "apply_security_updates": "playbooks/maintenance/security_updates.yml",
    "configure_firewall": "playbooks/networking/configure_firewall.yml",
    "deploy_docker": "playbooks/deployment/deploy_docker.yml",
    "configure_webhooks": "playbooks/integration/configure_webhooks.yml"
}
