#!/usr/bin/env python3
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
OUT_DIR    = SCRIPT_DIR / "build/out"
RELEASE_DIR = SCRIPT_DIR / "release"

NAME = "plasma-patches-blossom"

RPMBUILD = Path.home() / "rpmbuild"

# Installed with mode 755
BIN_FILES = {
    "org.kde.plasma.battery.so":    "/usr/lib64/qt6/plugins/plasma/applets/org.kde.plasma.battery.so",
    "org.kde.plasma.systemtray.so": "/usr/lib64/qt6/plugins/plasma/applets/org.kde.plasma.systemtray.so",
    "plasmashell":                  "/usr/bin/plasmashell",
    "patch_config.py":              "/usr/lib/plasma-patches-blossom/patch_config.py",
    "org.kde.plasma.digitalclock.so": "/usr/lib64/qt6/plugins/plasma/applets/org.kde.plasma.digitalclock.so",
    "libdigitalclockplugin.so":       "/usr/lib64/qt6/qml/org/kde/plasma/private/digitalclock/libdigitalclockplugin.so",
}

# Installed with mode 644
DATA_FILES = {
    "PanelConfiguration.qml": "/usr/share/plasma/shells/org.kde.plasma.desktop/contents/configuration/PanelConfiguration.qml",
    "DesktopEditMode.qml":    "/usr/share/plasma/shells/org.kde.plasma.desktop/contents/views/DesktopEditMode.qml",
}


def ask(prompt, default):
    if "--batch" in sys.argv:
        return default
    val = input(f"{prompt} [{default}]: ").strip()
    return val or default


def run(cmd, **kw):
    kw.setdefault("check", True)
    subprocess.run(cmd, **kw)


def main():
    version_file = SCRIPT_DIR / "VERSION"
    current_version = version_file.read_text().strip() if version_file.is_file() else "1.0"

    version   = ask("Version",   current_version)
    release   = ask("Release",   "1")
    changelog = ask("Changelog", f"packaged {NAME} {version}")

    if version != current_version:
        version_file.write_text(version + "\n")

    print("Initialising submodules …")
    run(["git", "submodule", "update", "--init", "--depth", "1"], cwd=SCRIPT_DIR)

    run([sys.executable, str(SCRIPT_DIR / "build.py")])

    for d in ("SPECS", "SOURCES", "BUILD", "RPMS", "SRPMS"):
        (RPMBUILD / d).mkdir(parents=True, exist_ok=True)
    RELEASE_DIR.mkdir(exist_ok=True)

    all_files = {**BIN_FILES, **DATA_FILES}

    if shutil.which("chrpath"):
        for fname in BIN_FILES:
            run(["chrpath", "-d", str(OUT_DIR / fname)], check=False)

    stage = RPMBUILD / "BUILD" / f"{NAME}-{version}"
    if stage.exists(): shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for fname in all_files:
        shutil.copy2(OUT_DIR / fname, stage / fname)

    tarball = RPMBUILD / "SOURCES" / f"{NAME}-{version}.tar.gz"
    run(["tar", "-czf", str(tarball), "-C", str(stage.parent), stage.name])

    date_str = datetime.now().strftime("%a %b %d %Y")
    install_lines = "\n".join([
        *[f'install -Dm 755 {f} %{{buildroot}}{dest}' for f, dest in BIN_FILES.items()],
        *[f'install -Dm 644 {f} %{{buildroot}}{dest}' for f, dest in DATA_FILES.items()],
    ])
    files_lines = "\n".join(all_files.values())
    system_files = " ".join(v for v in all_files.values() if not v.startswith("/usr/lib/plasma-patches-blossom"))

    spec = f"""\
%global debug_package %{{nil}}

Name:           {NAME}
Version:        {version}
Release:        {release}%{{?dist}}
Summary:        Patched KDE Plasma components for BlossomOS
License:        LGPL-2.0-or-later
URL:            https://codeberg.org/BlossomOS/plasma-blossom-patches
Source0:        %{{name}}-%{{version}}.tar.gz

Requires:       plasma-workspace
Requires:       powerdevil
Requires:       plasma-desktop
Requires:       python3

BuildArch:      x86_64

%description
Patched KDE Plasma applet plugins for BlossomOS:
- org.kde.plasma.battery: precise per-percent icon resolution
- org.kde.plasma.systemtray: expander arrow on far left, new SNI items hidden by default
- org.kde.plasma.desktop: panel reset-to-default button in edit mode

%prep
%autosetup

%build

%install
{install_lines}

%post
rm -f /usr/share/plasma/avatars/*Konq*.png /usr/share/plasma/avatars/Katie.png

REAL_USER="${{SUDO_USER:-$(logname 2>/dev/null || true)}}"
if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
    RUID=$(id -u "$REAL_USER")
    su -s /bin/bash "$REAL_USER" -c \
        "python3 /usr/lib/plasma-patches-blossom/patch_config.py" || true
    su -s /bin/bash "$REAL_USER" -c \
        "XDG_RUNTIME_DIR=/run/user/$RUID DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$RUID/bus systemctl --user restart plasma-plasmashell" || true
fi

%pre
for f in {system_files}; do
    [ -f "$f" ] && [ ! -f "$f.orig" ] && cp "$f" "$f.orig" || true
done

%preun
if [ $1 -eq 0 ]; then
    for f in {system_files}; do
        [ -f "$f.orig" ] && mv "$f.orig" "$f" || true
    done
fi

%files
{files_lines}

%changelog
* {date_str} packager - {version}-{release}
- {changelog}
"""

    spec_path = RPMBUILD / "SPECS" / f"{NAME}.spec"
    spec_path.write_text(spec)

    if not shutil.which("rpmbuild"):
        sys.exit("rpmbuild not found")

    run(["rpmbuild", "-bb", str(spec_path)])

    for rpm in (RPMBUILD / "RPMS").rglob(f"{NAME}-{version}-{release}*.rpm"):
        shutil.copy2(rpm, RELEASE_DIR / rpm.name)
        print(f"→ release/{rpm.name}")


if __name__ == "__main__":
    main()
