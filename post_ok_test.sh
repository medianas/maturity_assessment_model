#!/bin/bash
# Запускается после успешного bootstrap cluster-tiers scenario=ok.
# Делает прогон, сохраняет результаты, выводит сводку.

set -e
cd /c/diploma

echo "============================================================"
echo "  POST-BOOTSTRAP: cluster-tiers scenario=ok (real GitLab + Redmine + Mattermost)"
echo "============================================================"
date

echo ""
echo "[1/4] Проверка реального состояния ВМ через verify_cluster.sh"
echo "============================================================"
cd vagrant/devsecops/cluster-tiers
ls verify_cluster.sh 2>/dev/null || cp ../cluster-base/verify_cluster.sh .
# Подставляем имена tiers в verify
bash -c "
for n in node-gitlab-tr node-redmine-tr node-mattermost-tr; do
  echo ''
  echo '=== '\$n' ==='
  vagrant ssh \$n -c 'echo Listening; ss -tlnp 2>/dev/null | awk \"/:22 |:80 |:443 |:3000|:8065|:8080/\"; echo; echo Docker; sudo docker ps --format \"{{.Names}}: {{.Status}}\" 2>/dev/null; echo; echo /etc/devsec; ls /etc/devsec/ 2>/dev/null'
done
" 2>&1 | head -80
cd ../../..

echo ""
echo "[2/4] run_demo_cluster_real.py tiers — полный пайплайн"
echo "============================================================"
python run_demo_cluster_real.py tiers > reports/devsecops/cluster-tiers_ok_run.txt 2>&1
echo "Exit: $?"
tail -60 reports/cluster-tiers_v2_ok_run.txt

echo ""
echo "[3/4] Извлечение последнего отчёта из БД"
echo "============================================================"
python -c "
import sqlite3, json
conn = sqlite3.connect('reports.db')
rows = list(conn.execute('SELECT id, node_ip, timestamp FROM reports WHERE node_ip LIKE \"192.168.58.%\" ORDER BY id DESC LIMIT 5'))
for r in rows:
    print(f'ID {r[0]:>3} | {r[1]:<16} | {r[2]}')
"

echo ""
echo "[4/4] halt cluster-tiers"
echo "============================================================"
cd vagrant/devsecops/cluster-tiers && vagrant halt 2>&1 | tail -5
cd ../../..

echo ""
echo "============================================================"
echo "  cluster-tiers scenario=ok TEST COMPLETED"
echo "============================================================"
