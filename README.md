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