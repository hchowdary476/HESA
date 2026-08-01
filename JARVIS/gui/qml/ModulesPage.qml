// ModulesPage.qml — Active Modules Management — Full Table View
// Shows all 6 modules with status, heartbeat, and uptime columns.
// Data sourced from jarvis.activeModulesStatus (cached, no GUI-thread I/O).

import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Item {
    id: modPageRoot

    // ── Column width constants ────────────────────────────────────────────
    readonly property int colIndicator: 18
    readonly property int colName:      180
    readonly property int colStatus:    90
    readonly property int colHB:        100
    readonly property int colUptime:    100
    readonly property int colSpacing:   10

    // ── Header separator component ────────────────────────────────────────
    component ColHeader: Text {
        font.family: "Consolas"
        font.pixelSize: 8
        font.bold: true
        color: "#4a8aaa"
        verticalAlignment: Text.AlignVCenter
    }

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: 32
        contentHeight: Math.max(flickable.height, mainCol.implicitHeight)
        clip: true
        focus: true

        Keys.onUpPressed: flickable.contentY = Math.max(0, flickable.contentY - 40)
        Keys.onDownPressed: flickable.contentY = Math.min(flickable.contentHeight - flickable.height, flickable.contentY + 40)
        Keys.onPressed: {
            if (event.key === Qt.Key_PageUp) {
                flickable.contentY = Math.max(0, flickable.contentY - flickable.height)
                event.accepted = true
            } else if (event.key === Qt.Key_PageDown) {
                flickable.contentY = Math.min(flickable.contentHeight - flickable.height, flickable.contentY + flickable.height)
                event.accepted = true
            } else if (event.key === Qt.Key_Home) {
                flickable.contentY = 0
                event.accepted = true
            } else if (event.key === Qt.Key_End) {
                flickable.contentY = flickable.contentHeight - flickable.height
                event.accepted = true
            }
        }

        ScrollBar.vertical: ScrollBar {
            id: modScrollBar
            policy: ScrollBar.AsNeeded
            contentItem: Rectangle {
                implicitWidth: 6
                implicitHeight: 100
                radius: 3
                color: "#00BFFF"
                opacity: modScrollBar.active ? 0.8 : 0.4
                Behavior on opacity { NumberAnimation { duration: 150 } }
            }
            background: Rectangle {
                implicitWidth: 6
                color: "transparent"
            }
        }

        ColumnLayout {
            id: mainCol
            width: flickable.width
            spacing: 16

        // ── Page title ────────────────────────────────────────────────────
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Text {
                text: "ACTIVE MODULES"
                font.family: JarvisFont.orbitron
                font.pixelSize: 20
                font.bold: true
                color: "#00BFFF"
            }
            Item { Layout.fillWidth: true }
            // Live indicator
            Row {
                spacing: 6
                Rectangle {
                    width: 6; height: 6; radius: 3
                    color: "#00FF9D"
                    anchors.verticalCenter: parent.verticalCenter
                    SequentialAnimation on opacity {
                        loops: Animation.Infinite
                        NumberAnimation { from: 1.0; to: 0.2; duration: 700 }
                        NumberAnimation { from: 0.2; to: 1.0; duration: 700 }
                    }
                }
                Text {
                    text: "LIVE"
                    font.family: "Consolas"; font.pixelSize: 9; font.bold: true
                    color: "#00FF9D"
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        Rectangle { width: 260; height: 1; color: "#004b73" }

        // ── Column headers ────────────────────────────────────────────────
        RowLayout {
            Layout.fillWidth: true
            height: 20
            spacing: colSpacing

            Item { Layout.preferredWidth: colIndicator }

            ColHeader {
                text: "MODULE NAME"
                Layout.preferredWidth: colName
            }
            ColHeader {
                text: "STATUS"
                Layout.preferredWidth: colStatus
            }
            ColHeader {
                text: "LAST HEARTBEAT"
                Layout.preferredWidth: colHB
            }
            ColHeader {
                text: "UPTIME"
                Layout.preferredWidth: colUptime
            }
        }

        // Thin separator under headers
        Rectangle { Layout.fillWidth: true; height: 1; color: "#001e33" }

        // ── Module rows ───────────────────────────────────────────────────
        Repeater {
            model: jarvis.activeModulesStatus !== "[]" ? JSON.parse(jarvis.activeModulesStatus) : []

            delegate: Item {
                Layout.fillWidth: true
                height: 46

                // Hover highlight
                Rectangle {
                    anchors.fill: parent
                    color: rowMouse.containsMouse ? "#08192a" : "transparent"
                    radius: 3
                    Behavior on color { ColorAnimation { duration: 120 } }
                }

                // Left accent bar
                Rectangle {
                    width: 2; height: parent.height - 8
                    anchors.verticalCenter: parent.verticalCenter
                    color: modelData.color
                    opacity: 0.8
                    radius: 1
                }

                RowLayout {
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter }
                    anchors.leftMargin: 8
                    spacing: colSpacing
                    height: parent.height

                    // Status indicator dot
                    Item {
                        Layout.preferredWidth: colIndicator
                        Layout.alignment: Qt.AlignVCenter
                        Rectangle {
                            width: 8; height: 8; radius: 4
                            color: modelData.color
                            anchors.centerIn: parent
                            SequentialAnimation on opacity {
                                loops: Animation.Infinite
                                running: modelData.status === "ONLINE"
                                NumberAnimation { from: 1.0; to: 0.2; duration: 900; easing.type: Easing.InOutQuad }
                                NumberAnimation { from: 0.2; to: 1.0; duration: 900; easing.type: Easing.InOutQuad }
                            }
                        }
                    }

                    // Module name
                    Text {
                        text: modelData.name
                        font.family: "Consolas"; font.pixelSize: 11; font.bold: true
                        color: "#D6F5FF"
                        Layout.preferredWidth: colName
                        elide: Text.ElideRight
                        clip: true
                        verticalAlignment: Text.AlignVCenter
                        Layout.alignment: Qt.AlignVCenter
                    }

                    // Status badge
                    Rectangle {
                        Layout.preferredWidth: colStatus
                        Layout.preferredHeight: 20
                        Layout.alignment: Qt.AlignVCenter
                        color: modelData.color + "18"
                        border.color: modelData.color
                        border.width: 1
                        radius: 3
                        clip: true
                        Text {
                            anchors.centerIn: parent
                            width: parent.width - 6
                            text: modelData.status
                            font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true
                            color: modelData.color
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                        }
                    }

                    // Last heartbeat
                    Text {
                        text: modelData.last_heartbeat || "N/A"
                        font.family: "Consolas"; font.pixelSize: 10
                        color: "#4a8aaa"
                        Layout.preferredWidth: colHB
                        elide: Text.ElideRight
                        clip: true
                        verticalAlignment: Text.AlignVCenter
                        Layout.alignment: Qt.AlignVCenter
                    }

                    // Uptime
                    Text {
                        text: modelData.uptime || "00:00:00"
                        font.family: "Consolas"; font.pixelSize: 10
                        color: "#3a6a8a"
                        Layout.preferredWidth: colUptime
                        elide: Text.ElideRight
                        clip: true
                        verticalAlignment: Text.AlignVCenter
                        Layout.alignment: Qt.AlignVCenter
                    }
                }

                // Row hover handler
                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                }

                // Bottom divider
                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left; anchors.right: parent.right
                    height: 1
                    color: "#0a1e30"
                }
            }
        }

        // Summary row
        RowLayout {
            Layout.fillWidth: true
            spacing: 24
            Item { Layout.fillWidth: true }
            Text {
                text: {
                    var data = jarvis.activeModulesStatus !== "[]" ? JSON.parse(jarvis.activeModulesStatus) : []
                    var online = data.filter(function(m) { return m.status === "ONLINE" }).length
                    return online + " / " + data.length + " ONLINE"
                }
                font.family: JarvisFont.orbitron; font.pixelSize: 12; font.bold: true
                color: "#00FF9D"
            }
        }

        Item { Layout.fillHeight: true }
    }
}
}
