#!/bin/bash
set -e

SERVER=root@jamsite.local
NO_CACHE=""

for arg in "$@"; do
  case $arg in
    --no-cache) NO_CACHE="--no-cache" ;;
  esac
done

echo "=== Pulling latest code ==="
ssh $SERVER "cd /root/jamsite && git pull"

echo ""
echo "=== Rebuilding Docker container ==="
ssh $SERVER "cd /root && docker compose build jamsite $NO_CACHE && docker compose down && docker compose up -d"

echo ""
echo "=== Downloading songs ==="
ssh $SERVER "docker exec root-jamsite-1 /src/.venv/bin/jamsite --download"

echo ""
echo "=== Stopping Gotenberg ==="
ssh $SERVER "cd /root && docker compose stop gotenberg"

echo ""
echo "=== Done ==="
