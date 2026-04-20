/*
    SPDX-FileCopyrightText: 2011 Viranch Mehta <viranch.mehta@gmail.com>
    SPDX-FileCopyrightText: 2013 Kai Uwe Broulik <kde@privat.broulik.de>

    SPDX-License-Identifier: LGPL-2.0-or-later
*/

import QtQuick

import org.kde.kirigami as Kirigami

Item {
    id: root

    property bool hasBattery
    property int percent
    property bool pluggedIn
    property string batteryType
    property bool active: false
    property string powerProfileIconName: ""
    property bool preferSymbolic: false

    Kirigami.Icon {
        anchors.fill: parent
        source: "battery-missing" + (root.preferSymbolic ? "-symbolic" : "")
        visible: !root.hasBattery && !otherBatteriesIcon.visible
        active: root.active
    }

    Item {
        id: levelIconContainer
        anchors.fill: parent
        visible: root.hasBattery && !otherBatteriesIcon.visible

        readonly property string chargingSuffix: root.pluggedIn ? "-charging" : ""
        readonly property string profileSuffix: root.powerProfileIconName.length > 0 ? "-profile-" + root.powerProfileIconName : ""
        readonly property string symSuffix: root.preferSymbolic ? "-symbolic" : ""
        // Searching for next available icon by percentage
        readonly property var candidates: {
            const p = root.percent;
            return Array.from({
                length: 101
            }, (_, i) => i).sort((a, b) => {
                const d = Math.abs(b - p) - Math.abs(a - p);
                return d !== 0 ? d : b - a;
            });
        }

        Repeater {
            model: levelIconContainer.candidates

            Kirigami.Icon {
                required property int modelData
                anchors.fill: levelIconContainer
                source: "battery-level-" + modelData + levelIconContainer.chargingSuffix + levelIconContainer.profileSuffix + levelIconContainer.symSuffix
                active: root.active
                visible: valid
            }
        }
    }

    // Generic icon for other types of batteries
    Kirigami.Icon {
        id: otherBatteriesIcon
        anchors.fill: parent
        source: elementForType(root.batteryType) + (root.preferSymbolic ? "-symbolic" : "")
        visible: elementForType(root.batteryType) !== ""
        active: root.active

        function elementForType(t: string): string {
            switch (t) {
            case "Mouse":
                return "input-mouse-battery";
            case "Keyboard":
                return "input-keyboard-battery";
            case "Pda":
                return "phone-battery";
            case "Phone":
                return "phone-battery";
            case "Ups":
                return "battery-ups";
            case "GamingInput":
                return "input-gaming-battery";
            case "Bluetooth":
                return "preferences-system-bluetooth-battery";
            case "Headphone":
                return "audio-headphones-battery";
            case "Headset":
                return "audio-headset-battery";
            default:
                return "";
            }
        }
    }
}
