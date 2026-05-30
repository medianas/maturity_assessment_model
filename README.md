# maturity-assessment-model

Инструмент, реализующий модель оценки зрелости практического применения
фреймворков **DevSecOps** и **Agile** для повышения уровня кибербезопасности.

## Возможности

- Аудит инфраструктуры: HTTPS, SSH, firewall, интеграции с GitLab/Redmine/Mattermost (paramiko + TCP-сокеты)
- Оценка зрелости по **10 критериям** (синтез CMMI, DevSecOps, Agile, SPM)
- Автоматическая генерация и выполнение **Ansible-плейбуков** для исправлений
- Хранение отчётов в SQLite, экспорт JSON/HTML
- Файловое логирование (`logs/assessment_YYYY-MM-DD.log`)
- **Кластерное тестирование** на 3 предсобранных Vagrant-окружениях (mock и real-режимы)
- **Реальная автоматизация** через выделенную Ansible control-node (4-я ВМ в каждом кластере)
- **Юнит-тесты**: 37 pytest-тестов

## Адаптация под любой проект

Проект устроен как настраиваемая модель оценки зрелости: один и тот же
пайплайн можно применять к разным организациям, стендам и наборам внутренних
требований. Меняются входные узлы, профиль аудита, правила исправлений,
Ansible-плейбуки и рекомендации, а общий цикл остаётся одинаковым:

```text
IP-адреса + SSH-доступ + профиль
        -> аудит
        -> выявление несоответствий
        -> выбор правил исправления
        -> запуск Ansible
        -> отчёт по уровню зрелости
```

### Где задавать IP-адреса машин

Для обычного запуска целевые машины передаются через CLI:

```bash
python cli.py --ip 10.10.1.15 10.10.1.16 10.10.1.17 \
              --user admin --password pass \
              --profile admin \
              --format json --output report.json
```

Для демонстрационных кластеров IP-адреса заданы в словаре `CLUSTERS`:

- `run_demo_cluster.py` — реальный аудит, mock-automation;
- `run_demo_cluster_real.py` — реальный аудит и реальный запуск Ansible через control-node.

Пример структуры:

```python
CLUSTERS = {
    "base": {
        "title": "Infrastructure Maturity Baseline",
        "nodes": [
            {"ip": "192.168.56.10", "name": "node-critical"},
            {"ip": "192.168.56.20", "name": "node-app"},
            {"ip": "192.168.56.30", "name": "node-secure"},
        ],
    },
}
```

### Где задавать правила и профили

Основная точка настройки — `config.py`.

`AUDIT_PROFILES` определяет, какие проверки входят в профиль:

```python
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
    }
}
```

`CORRECTION_RULES` связывает найденное нарушение с корректирующим действием:

```python
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
    }
}
```

Так модель можно подстроить под конкретную организацию: заменить набор
проверок, приоритеты, описания, рекомендации и Ansible-плейбуки. Например,
вместо GitLab/Redmine/Mattermost можно описать собственный Git-сервер,
Service Desk и корпоративный мессенджер.

### Как адаптировать требования

1. Добавить или изменить профиль в `AUDIT_PROFILES`.
2. Убедиться, что нужная проверка реализована в `audit.py`.
3. Добавить правило исправления в `CORRECTION_RULES`.
4. Связать имя проверки с правилом в `decision.py`.
5. Добавить или заменить Ansible-плейбук в `playbooks/`.
6. Запустить CLI с IP-адресами нужных машин.

Важно: IP-адреса, профили, рекомендации и правила исправления меняются
конфигурационно. Добавление принципиально нового типа проверки требует
небольшой доработки `audit.py` и связи с правилом в `decision.py`.

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# или
source .venv/bin/activate       # Linux/Mac
pip install -r requirements-dev.txt
```

## Способы запуска

```bash
# Однонодовая демонстрация (моки, без сети)
python run_demo.py

# Та же демонстрация, но с CALL/RETURN-логированием каждого вызова метода
python run_demo_traced.py

# Кластерная демонстрация на реальных Vagrant-ВМ (mock-automation)
#    Стенд platform — generic Ubuntu с разными ролями
cd vagrant/platform/cluster-base && vagrant up && cd ../../..
python run_demo_cluster.py base       # Infrastructure Maturity Baseline
python run_demo_cluster.py lifecycle  # dev → staging → prod
python run_demo_cluster.py tiers      # bastion / internal / public

#    Стенд devsecops — GitLab CE / Redmine / Mattermost через docker-compose
cd vagrant/devsecops/cluster-base && vagrant up && cd ../../..
python run_demo_cluster_real.py base                  # default стенд = devsecops
python run_demo_cluster_real.py base --stand=platform # platform-стенд
python run_demo_cluster_real.py base --domain=devsecops  # фильтрация отчёта

# 6. Merged-стенд: гетерогенный кластер (один gitlab=broken, один redmine=missing,
#    один mattermost=ok) — за один прогон видны все 3 семантически разных состояния.
cd vagrant/merged/cluster-merged && vagrant up && cd ../../..
python run_demo_cluster_real.py merged                # оба домена в одном отчёте
# Всего 7 стендов: 3 platform + 3 devsecops + 1 merged.
```

## Документация
### Диаграмма вариантов использования (Use Case Diagram)
<img width="974" height="169" alt="image" src="https://github.com/user-attachments/assets/872a0f0f-47d2-447f-9e59-f3837299e2f8" />



### Диаграмма последовательности (Sequence Diagram)
<img width="974" height="845" alt="image" src="https://github.com/user-attachments/assets/99599bfb-79eb-4cde-90cd-ffe433a996bb" />



### Диаграмма классов (Class Diagram)
<img width="974" height="354" alt="image" src="https://github.com/user-attachments/assets/fb4c62c2-f2b5-42d9-b32b-a46bc41659ad" />



### Диаграмма компонентов (Component Diagram)
<img width="974" height="409" alt="image" src="https://github.com/user-attachments/assets/caaee7dc-7f2d-4d41-99d4-41039202ade8" />



### Диаграмма деятельности (Activity Diagram)
<img width="900" height="1424" alt="image" src="https://github.com/user-attachments/assets/b9b66b22-d703-44de-8506-50798916bb9b" />



### Диаграмма сущностей и их связей (ER Diagram)
<img width="974" height="1342" alt="image" src="https://github.com/user-attachments/assets/72b79576-7e74-4051-99ca-a35c57750ebb" />



### Диаграмма пакетов (Package Diagram)
<img width="974" height="336" alt="image" src="https://github.com/user-attachments/assets/f7623d8a-673b-4a9a-aa3c-c8be8cd429dd" />


