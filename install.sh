#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLASMOID_DIR="/usr/share/plasma/plasmoids/org.kde.plasma.battery"
ROLLBACK_DIR="$HOME/.local/share/plasma/plasmoids/org.kde.plasma.battery.backup"
APPLET_SO="/usr/lib64/qt6/plugins/plasma/applets/org.kde.plasma.battery.so"

if [ "${1:-}" = "--rollback" ]; then
    [ -d "$ROLLBACK_DIR" ] || { echo "No rollback backup found at $ROLLBACK_DIR" >&2; exit 1; }
    command -v sudo >/dev/null 2>&1 || { echo "sudo required" >&2; exit 1; }

    sudo bash -c "
        for f in main.qml CompactRepresentation.qml BatteryItem.qml PopupDialog.qml \
                  PowerProfileItem.qml InhibitionHint.qml InhibitionItem.qml \
                  BatteryIcon.qml BadgeOverlay.qml; do
            rm -f '${PLASMOID_DIR}/contents/ui/\$f'
        done
        rm -f '${PLASMOID_DIR}/contents/config/main.xml' '${PLASMOID_DIR}/metadata.json'
    "
    if [ -d "$ROLLBACK_DIR/contents/ui" ] && [ "$(ls -A "$ROLLBACK_DIR/contents/ui" 2>/dev/null)" ]; then
        sudo cp -a "$ROLLBACK_DIR/contents/ui/." "$PLASMOID_DIR/contents/ui/"
    fi
    if [ -f "$ROLLBACK_DIR/metadata.json" ]; then
        sudo cp -a "$ROLLBACK_DIR/metadata.json" "$PLASMOID_DIR/metadata.json"
    fi
    if [ -f "${APPLET_SO}.bak" ]; then
        sudo mv "${APPLET_SO}.bak" "$APPLET_SO"
    fi

    systemctl --user restart plasma-plasmashell
    exit 0
fi

RPM_FILE="$(find "$SCRIPT_DIR/release" -name "plasma-battery-precise-*.rpm" 2>/dev/null | sort -V | tail -1 || true)"
if [ -z "$RPM_FILE" ]; then
    printf '\n\n\n' | bash "$SCRIPT_DIR/release.sh" >/dev/null
    RPM_FILE="$(find "$SCRIPT_DIR/release" -name "plasma-battery-precise-*.rpm" | sort -V | tail -1)"
fi

command -v sudo >/dev/null 2>&1 || { echo "sudo required" >&2; exit 1; }

mkdir -p "$ROLLBACK_DIR/contents/ui" "$ROLLBACK_DIR/contents/config"
if [ -d "$PLASMOID_DIR/contents/ui" ] && [ "$(ls -A "$PLASMOID_DIR/contents/ui" 2>/dev/null)" ]; then
    cp -a "$PLASMOID_DIR/contents/ui/." "$ROLLBACK_DIR/contents/ui/"
fi
if [ -f "$PLASMOID_DIR/metadata.json" ]; then
    cp -a "$PLASMOID_DIR/metadata.json" "$ROLLBACK_DIR/metadata.json"
fi

if ! sudo rpm -Uvh --force "$RPM_FILE" 2>/dev/null; then
    rm -f "$RPM_FILE"
    printf '\n\n\n' | bash "$SCRIPT_DIR/release.sh" >/dev/null
    RPM_FILE="$(find "$SCRIPT_DIR/release" -name "plasma-battery-precise-*.rpm" | sort -V | tail -1)"
    sudo rpm -Uvh --force "$RPM_FILE"
fi

systemctl --user restart plasma-plasmashell

echo "Done. To undo: $0 --rollback"
