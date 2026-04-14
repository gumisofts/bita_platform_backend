#!/usr/bin/env bash
# Deploy the latest code to production.
#
# Usage:
#   ./scripts/deploy-production.sh              # full deploy (migrate + collectstatic + restart)
#   ./scripts/deploy-production.sh migrate      # only run migrations
#   ./scripts/deploy-production.sh collectstatic
#   ./scripts/deploy-production.sh restart      # only restart services
#   ./scripts/deploy-production.sh nginx        # only update nginx config
#   ./scripts/deploy-production.sh domains      # only update Django env domains
#   ./scripts/deploy-production.sh nginx,domains  # nginx + Django env (no restart)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ANSIBLE_DIR="$REPO_ROOT/config/ansible"
INVENTORY="$ANSIBLE_DIR/ini.yml"
PRIVATE_KEY="${PRIVATE_KEY:-$HOME/.ssh/contabo.pem}"

cd "$REPO_ROOT"

if ! command -v ansible-playbook &>/dev/null; then
  echo "Error: ansible-playbook not found. Install Ansible first."
  exit 1
fi

TAGS="${1:-}"

if [[ -n "$TAGS" ]]; then
  echo "==> Deploying to PRODUCTION — tags: $TAGS"
  ansible-playbook -i "$INVENTORY" "$ANSIBLE_DIR/deploy.yml" \
    --private-key "$PRIVATE_KEY" \
    --ask-become-pass \
    --tags "$TAGS"
else
  echo "==> Full deploy to PRODUCTION"
  ansible-playbook -i "$INVENTORY" "$ANSIBLE_DIR/deploy.yml" \
    --private-key "$PRIVATE_KEY" \
    --ask-become-pass
fi

echo "==> Deployment finished."
