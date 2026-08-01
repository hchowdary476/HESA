// BottomDock.qml — Navigation tab bar at bottom of screen

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: dockRoot
    color: "transparent"

    property string activePage: "dashboard"
    signal pageSelected(string page)

    property var tabs: [
        { label: "DASHBOARD",   key: "dashboard",   icon: "⬡" },
        { label: "SYSTEM",      key: "system",      icon: "⬡" },
        { label: "MODULES",     key: "modules",     icon: "⬡" },
        { label: "CYBER SECURITY", key: "cybersecurity", icon: "⬡" },
        { label: "DIAGNOSTICS", key: "diagnostics", icon: "⬡" },
        { label: "AI & ML",     key: "ai_ml",       icon: "⬡" },
        { label: "SETTINGS",    key: "settings",    icon: "⬡" },
        { label: "HELP",        key: "help",        icon: "⬡" },
    ]

    // Top separator
    Rectangle {
        anchors.top: parent.top
        width: parent.width; height: 1
        color: "#004b73"
    }

    Row {
        anchors.centerIn: parent
        spacing: 15

        Repeater {
            model: dockRoot.tabs

            delegate: Column {
                spacing: 0
                width: 90

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: modelData.icon
                    font.pixelSize: 16
                    color: dockRoot.activePage === modelData.key ? "#00BFFF" : "#4D94B3"

                    Behavior on color { ColorAnimation { duration: 200 } }
                }

                Rectangle {
                    width: 90; height: 22
                    color: dockRoot.activePage === modelData.key ? "#0c1826"
                         : tabHover.containsMouse                ? "#08101a"
                         : "transparent"
                    radius: 3

                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        font.family: JarvisFont.orbitron
                        font.pixelSize: 10
                        color: dockRoot.activePage === modelData.key ? "#D6F5FF"
                             : tabHover.containsMouse                ? "#80C6E5"
                             : "#4D94B3"

                        Behavior on color { ColorAnimation { duration: 150 } }
                    }

                    // Active indicator bar
                    Rectangle {
                        visible: dockRoot.activePage === modelData.key
                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 40; height: 2
                        color: "#00BFFF"
                        radius: 1
                    }

                    MouseArea {
                        id: tabHover
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: dockRoot.pageSelected(modelData.key)
                        cursorShape: Qt.PointingHandCursor
                    }
                }
            }
        }
    }
}
