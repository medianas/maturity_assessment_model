#!/bin/bash
# Прогон тестов сразу после успешного bootstrap'а cluster-base.
# Запускается автоматически когда bootstrap finishes.

set -e
cd /c/diploma

echo "============================================================"
echo "  POST-BOOTSTRAP TEST: cluster-base scenario=missing"
echo "============================================================"

echo ""
echo "[1/4] verify_cluster.sh — независимая проверка реального состояния ВМ"
echo "============================================================"
cd vagrant/devsecops/cluster-base && bash verify_cluster.sh 2>&1 | head -60
cd ../../..

echo ""
echo "[2/4] run_demo_cluster_real.py base — полный пайплайн"
echo "============================================================"
python run_demo_cluster_real.py base 2>&1 | tail -80

echo ""
echo "[3/4] Извлечение последнего отчёта из БД"
echo "============================================================"
python -c "
import sqlite3, json
conn = sqlite3.connect('reports.db')
rows = list(conn.execute('SELECT id, node_ip, timestamp FROM reports ORDER BY id DESC LIMIT 5'))
for r in rows:
    print(f'ID {r[0]:>3} | {r[1]:<16} | {r[2]}')
"

echo ""
echo "[4/4] Финальный pytest для regression"
echo "============================================================"
python -m pytest tests/ -q

echo ""
echo "============================================================"
echo "  POST-BOOTSTRAP TEST COMPLETED"
echo "============================================================"
