#!/bin/bash
set -e

NAME=plasma-battery-precise
CURRENT_VERSION=$(cat VERSION)

read -rp "Version [$CURRENT_VERSION]: " VERSION
VERSION=${VERSION:-$CURRENT_VERSION}

read -rp "Release [1]: " RELEASE
RELEASE=${RELEASE:-1}

read -rp "Changelog entry [packaged $NAME $VERSION]: " CHANGELOG
CHANGELOG=${CHANGELOG:-"packaged $NAME $VERSION"}

if [ "$VERSION" != "$CURRENT_VERSION" ]; then
    echo "$VERSION" > VERSION
    echo "Updated VERSION to $VERSION"
fi

RPMBUILD=~/rpmbuild
mkdir -p "$RPMBUILD"/{SPECS,SOURCES,BUILD,RPMS,SRPMS} release

tar -czf "$RPMBUILD/SOURCES/$NAME-$VERSION.tar.gz" \
    --transform "s|^\./|$NAME-$VERSION/|" \
    --exclude=./.git --exclude=./release \
    .

cat > "$RPMBUILD/SPECS/$NAME.spec" << EOF
Name:           $NAME
Version:        $VERSION
Release:        $RELEASE%{?dist}
Summary:        Battery widget with precise per-percent icon resolution
License:        MIT
URL:            https://codeberg.org/BlossomOS/plasma-battery-precise
Source0:        %{name}-%{version}.tar.gz

Requires:       powerdevil
Requires:       kf6-kirigami2
Requires:       plasma-workspace

BuildArch:      noarch

%description
Battery widget for KDE Plasma 6 that picks the closest available icon for
the exact charge percentage, compatible with any icon pack resolution.

%prep
%autosetup

%build

%install
install -Dm 644 metadata.json %{buildroot}/usr/share/plasma/plasmoids/org.kde.plasma.battery/metadata.json
for f in contents/ui/*.qml; do
    install -Dm 644 "\$f" %{buildroot}/usr/share/plasma/plasmoids/org.kde.plasma.battery/"\$f"
done
install -Dm 644 contents/config/main.xml %{buildroot}/usr/share/plasma/plasmoids/org.kde.plasma.battery/contents/config/main.xml

%pre
PLASMOID=/usr/share/plasma/plasmoids/org.kde.plasma.battery
BACKUP=/var/lib/%{name}/backup
if [ -d "\$PLASMOID/contents/ui" ] && [ "\$(ls -A "\$PLASMOID/contents/ui" 2>/dev/null)" ]; then
    mkdir -p "\$BACKUP/contents/ui"
    cp -a "\$PLASMOID/contents/ui/." "\$BACKUP/contents/ui/"
fi
if [ -f "\$PLASMOID/metadata.json" ]; then
    mkdir -p "\$BACKUP"
    cp -a "\$PLASMOID/metadata.json" "\$BACKUP/"
fi

%post
APPLET_SO=/usr/lib64/qt6/plugins/plasma/applets/org.kde.plasma.battery.so
if [ -f "\$APPLET_SO" ]; then
    mv "\$APPLET_SO" "\$APPLET_SO.bak"
fi

%preun
if [ \$1 -eq 0 ]; then
    PLASMOID=/usr/share/plasma/plasmoids/org.kde.plasma.battery
    BACKUP=/var/lib/%{name}/backup
    APPLET_SO=/usr/lib64/qt6/plugins/plasma/applets/org.kde.plasma.battery.so
    for f in main.qml CompactRepresentation.qml BatteryItem.qml PopupDialog.qml \
              PowerProfileItem.qml InhibitionHint.qml InhibitionItem.qml \
              BatteryIcon.qml BadgeOverlay.qml; do
        rm -f "\$PLASMOID/contents/ui/\$f"
    done
    rm -f "\$PLASMOID/contents/config/main.xml" "\$PLASMOID/metadata.json"
    if [ -d "\$BACKUP/contents/ui" ] && [ "\$(ls -A "\$BACKUP/contents/ui" 2>/dev/null)" ]; then
        cp -a "\$BACKUP/contents/ui/." "\$PLASMOID/contents/ui/"
    fi
    if [ -f "\$BACKUP/metadata.json" ]; then
        cp -a "\$BACKUP/metadata.json" "\$PLASMOID/metadata.json"
    fi
    rm -rf "\$BACKUP"
    if [ -f "\$APPLET_SO.bak" ]; then
        mv "\$APPLET_SO.bak" "\$APPLET_SO"
    fi
fi

%files
%license LICENSE.md
/usr/share/plasma/plasmoids/org.kde.plasma.battery/metadata.json
/usr/share/plasma/plasmoids/org.kde.plasma.battery/contents/ui/main.qml
/usr/share/plasma/plasmoids/org.kde.plasma.battery/contents/ui/CompactRepresentation.qml
/usr/share/plasma/plasmoids/org.kde.plasma.battery/contents/ui/BatteryItem.qml
/usr/share/plasma/plasmoids/org.kde.plasma.battery/contents/ui/PopupDialog.qml
/usr/share/plasma/plasmoids/org.kde.plasma.battery/contents/ui/PowerProfileItem.qml
/usr/share/plasma/plasmoids/org.kde.plasma.battery/contents/ui/InhibitionHint.qml
/usr/share/plasma/plasmoids/org.kde.plasma.battery/contents/ui/InhibitionItem.qml
/usr/share/plasma/plasmoids/org.kde.plasma.battery/contents/ui/BatteryIcon.qml
/usr/share/plasma/plasmoids/org.kde.plasma.battery/contents/ui/BadgeOverlay.qml
/usr/share/plasma/plasmoids/org.kde.plasma.battery/contents/config/main.xml

%changelog
* $(LC_TIME=C date "+%a %b %d %Y") packager - $VERSION-$RELEASE
- $CHANGELOG
EOF

if command -v rpmbuild >/dev/null 2>&1; then
    rpmbuild -ba "$RPMBUILD/SPECS/$NAME.spec"
    find "$RPMBUILD/RPMS" -name "$NAME-$VERSION-$RELEASE*.rpm" -exec cp {} release/ \;
else
    echo "rpmbuild not found, skipping RPM build."
fi

echo "Done: $(ls release/)"
