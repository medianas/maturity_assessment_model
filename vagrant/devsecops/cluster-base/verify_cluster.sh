#!/bin/bash
# Проверка реального состояния всех узлов кластера.
# Запуск из папки vagrant/:   bash verify_cluster.sh

SEP="================================================================="

check_node() {
  local node=$1
  echo ""
  echo "$SEP"
  echo "  Узел: $node"
  echo "$SEP"

  echo ""
  echo "--- Слушающие порты (22/80/443) ---"
  vagrant ssh "$node" -c "ss -tlnp 2>/dev/null | awk '/:22 |:80 |:443 /'" 2>/dev/null | sed 's/^/  /'

  echo ""
  echo "--- Эффективная SSH-конфигурация ---"
  vagrant ssh "$node" -c "sudo sshd -T 2>/dev/null | grep -E '^(permitrootlogin|passwordauthentication) '" 2>/dev/null | sed 's/^/  /'

  echo ""
  echo "--- nginx ---"
  vagrant ssh "$node" -c "if systemctl list-unit-files nginx.service &>/dev/null; then printf 'nginx.service: '; systemctl is-active nginx; else echo 'nginx: НЕ УСТАНОВЛЕН'; fi" 2>/dev/null | sed 's/^/  /'

  echo ""
  echo "--- ufw ---"
  vagrant ssh "$node" -c "printf 'ufw.service: '; systemctl is-active ufw 2>/dev/null; printf 'ufw статус:  '; sudo ufw status 2>/dev/null | head -1" 2>/dev/null | sed 's/^/  /'
}

for n in node-critical node-app node-secure; do
  check_node "$n"
done

echo ""
echo "$SEP"
echo "  Проверка завершена"
echo "$SEP"
