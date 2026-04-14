#!/usr/bin/env bash
# Bootstrap a new production server (run once, or when updating infrastructure).
#
# Usage:
#   ./scripts/setup-production.sh           # full bootstrap
#   ./scripts/setup-production.sh nginx     # only SSL + nginx tasks
#   ./scripts/setup-production.sh packages  # only system packages
#   ./scripts/setup-production.sh app       # only app + services
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
  echo "==> Bootstrapping PRODUCTION — tags: $TAGS"
  ansible-playbook -i "$INVENTORY" "$ANSIBLE_DIR/install.yml" \
    --private-key "$PRIVATE_KEY" \
    --ask-become-pass \
    --tags "$TAGS"
else
  echo "==> Full server bootstrap on PRODUCTION"
  ansible-playbook -i "$INVENTORY" "$ANSIBLE_DIR/install.yml" \
    --private-key "$PRIVATE_KEY" \
    --ask-become-pass
fi

echo "==> Bootstrap finished."
