// TitleBar.qml — Custom frameless window title bar

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: titleBar
    color: "transparent"

    signal minimizeRequested()
    signal maximizeRequested()
    signal closeRequested()
    signal dragStarted(real mx, real my)
    signal dragMoved(real gx, real gy)
    signal dragEnded()

    property string clockText: "00:00:00"

    Connections {
        target: jarvis
        function onClockUpdated(t) { titleBar.clockText = t }
    }

    // Drag area — covers the whole bar; window-control MouseAreas intercept
    // their own clicks first (natural z-order), so drag still works correctly.
    MouseArea {
        anchors.fill: parent
        onPressed: function(mouse) {
            titleBar.dragStarted(mouse.x, mouse.y)
        }
        onPositionChanged: function(mouse) {
            if (pressed) titleBar.dragMoved(mouse.globalX, mouse.globalY)
        }
        onReleased: titleBar.dragEnded()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ── Left: Logo + version ─────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            RowLayout {
                anchors { left: parent.left; verticalCenter: parent.verticalCenter; leftMargin: 30 }
                spacing: 15

                Text {
                    text: "≡"
                    font.family: JarvisFont.orbitron; font.pixelSize: 16; font.bold: true
                    color: "#80C6E5"
                }
                Text {
                    text: "HESA OS v2.0.0"
                    font.family: JarvisFont.orbitron; font.pixelSize: 12
                    color: "#80C6E5"
                }
            }
        }

        // ── Center: HESA title ──────────────────────────────────────────
        Column {
            Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
            spacing: 0
            Text {
                text: "HESA"
                font.family: JarvisFont.orbitron; font.pixelSize: 24; font.bold: true
                color: "#D6F5FF"
                anchors.horizontalCenter: parent.horizontalCenter
            }
            Text {
                text: "CONSCIOUSNESS ACTIVATED"
                font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true
                color: "#00BFFF"
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }

        // ── Right: Status + clock + controls ────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            RowLayout {
                anchors { right: parent.right; verticalCenter: parent.verticalCenter; rightMargin: 10 }
                spacing: 10

                Text {
                    text: "● ONLINE"
                    font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true
                    color: "#00FF9D"
                }
                Text {
                    text: titleBar.clockText
                    font.family: JarvisFont.orbitron; font.pixelSize: 12
                    color: "#80C6E5"
                }

                // Window controls
                Row {
                    id: controlRow
                    spacing: 4

                    Repeater {
                        model: [
                            { label: "─", action: "min" },
                            { label: "□", action: "max" },
                            { label: "✕", action: "cls" },
                        ]
                        delegate: Rectangle {
                            width: 28; height: 28
                            color: controlHover.containsMouse
                                        ? (modelData.action === "cls" ? "#FF3366" : "#0c1826")
                                        : "transparent"
                            radius: 3

                            Text {
                                anchors.centerIn: parent
                                text: modelData.label
                                font.pixelSize: 14
                                color: "#80C6E5"
                            }

                            MouseArea {
                                id: controlHover
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    if (modelData.action === "min") titleBar.minimizeRequested()
                                    else if (modelData.action === "max") titleBar.maximizeRequested()
                                    else titleBar.closeRequested()
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Bottom separator line
    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width; height: 1
        color: "#004b73"
    }
}
