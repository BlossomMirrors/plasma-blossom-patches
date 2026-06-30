#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--rollback" ]]; then
    sudo rpm -e plasma-patches-blossom 2>/dev/null || true
    systemctl --user restart plasma-plasmashell
    echo "Rolled back."
    exit 0
fi

sudo rpm-ostree unlock --hotfix | true || true

sudo dnf install -y 'dnf-command(builddep)'
sudo dnf builddep -y plasma-workspace
sudo dnf builddep -y powerdevil

python3 "$SCRIPT_DIR/release.py" --batch

RPM=$(ls -t "$SCRIPT_DIR/release/"plasma-patches-blossom-*.rpm 2>/dev/null | head -1)
[[ -z "$RPM" ]] && { echo "No RPM found in release/"; exit 1; }
sudo rpm -Uvh --force "$RPM"

systemctl --user restart plasma-plasmashell

echo "Done. To undo: bash $SCRIPT_DIR/install.sh --rollback"
