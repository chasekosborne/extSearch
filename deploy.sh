#!/usr/bin/env bash
# Environment overrides:
#   DEPLOY_BRANCH       Git branch to deploy (default: main)
#   VENV_PATH           Python venv directory (default: <repo>/.venv)
#   SKIP_SYSTEMD_RESTART   If set to 1, skip systemctl restart (local / debugging)
#   SKIP_WEB_RELOAD     If set to 1, skip Apache/Nginx reload when active

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$REPO_ROOT"

BRANCH="${DEPLOY_BRANCH:-main}"
VENV_PATH="${VENV_PATH:-$REPO_ROOT/.venv}"

echo "==> Repository: $REPO_ROOT"
echo "==> Branch: $BRANCH"

git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "==> Python venv: $VENV_PATH"
if [[ ! -x "$VENV_PATH/bin/python" ]]; then
  echo "    Creating venv"
  python3 -m venv "$VENV_PATH"
fi
"$VENV_PATH/bin/pip" install --upgrade pip
"$VENV_PATH/bin/pip" install -r "$REPO_ROOT/requirements.txt"
# gunicorn is used by systemd units but not listed in requirements.txt
"$VENV_PATH/bin/pip" install 'gunicorn>=22.0.0'

if [[ "${SKIP_SYSTEMD_RESTART:-0}" == "1" ]]; then
  echo "==> SKIP_SYSTEMD_RESTART=1 — not restarting extsearch-* services"
  exit 0
fi

echo "==> Restart extsearch services"
sudo systemctl restart extsearch-web extsearch-auth extsearch-worker

if [[ "${SKIP_WEB_RELOAD:-0}" == "1" ]]; then
  echo "==> SKIP_WEB_RELOAD=1 — skipping reverse proxy reload"
  exit 0
fi

if systemctl is-active --quiet apache2 2>/dev/null; then
  echo "==> Reload Apache"
  sudo apache2ctl configtest
  sudo systemctl reload apache2
elif systemctl is-active --quiet nginx 2>/dev/null; then
  echo "==> Reload Nginx"
  sudo nginx -t
  sudo systemctl reload nginx
fi

echo "==> Deploy finished"
