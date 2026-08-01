// HelpPage.qml — Interactive holographic help interface, voice command directory & keybindings

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: helpRoot

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: 32
        contentHeight: Math.max(flickable.height, helpLayout.implicitHeight)
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
            id: helpScrollBar
            policy: ScrollBar.AsNeeded
            contentItem: Rectangle {
                implicitWidth: 6
                implicitHeight: 100
                radius: 3
                color: "#00BFFF"
                opacity: helpScrollBar.active ? 0.8 : 0.4
                Behavior on opacity { NumberAnimation { duration: 150 } }
            }
            background: Rectangle {
                implicitWidth: 6
                color: "transparent"
            }
        }

        ColumnLayout {
            id: helpLayout
            width: parent.width
            spacing: 24

            // Header Section
            Column {
                spacing: 2
                Text {
                    text: "SYSTEM HELP & COMMAND DIRECTORY"
                    font.family: JarvisFont.orbitron; font.pixelSize: 22; font.bold: true
                    color: "#00BFFF"
                }
                Text {
                    text: "JARVIS HUD DOCUMENTATION & KEYBOARD SYSTEM BINDINGS"
                    font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true
                    color: "#00FF9D"
                }
            }

            Rectangle { width: 300; height: 1; color: "#004b73"; opacity: 0.6 }

            // Overview Section
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 90
                color: "#050814"
                border.color: "#004b73"
                border.width: 1
                radius: 4
                
                RowLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 14
                    Text {
                        text: "❖"
                        font.pixelSize: 28; font.bold: true; color: "#00BFFF"
                        Layout.alignment: Qt.AlignVCenter
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "JARVIS INTELLIGENCE INTERFACE SYSTEM"
                            font.family: JarvisFont.orbitron; font.pixelSize: 11; font.bold: true; color: "#D6F5FF"
                        }
                        Text {
                            text: "Welcome to the JARVIS QML HUD, sir. Below you will find all system key bindings, functional command schemas, and diagnostics tools directory. Use the command console or voice speech controls to execute core macros."
                            font.family: "Consolas"; font.pixelSize: 9; color: "#80C6E5"; wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            RowLayout {
                spacing: 16
                Layout.fillWidth: true

                // Left: Keyboard Shortcuts
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 320
                    color: "#08101a"
                    border.color: "#004b73"
                    radius: 4

                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 16; spacing: 12
                        Text { text: "SYSTEM KEY BINDINGS"; font.family: JarvisFont.orbitron; font.pixelSize: 11; font.bold: true; color: "#00BFFF" }
                        
                        Rectangle { Layout.fillWidth: true; height: 1; color: "#004b73"; opacity: 0.5 }

                        ColumnLayout {
                            spacing: 8
                            Layout.fillWidth: true

                            RowLayout {
                                Text { text: "[ Escape ]"; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#00FF9D"; width: 120 }
                                Text { text: "Returns to main Dashboard instantly."; font.family: "Consolas"; font.pixelSize: 9; color: "#80C6E5" }
                            }
                            RowLayout {
                                Text { text: "[ Alt + F4 ]"; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#00FF9D"; width: 120 }
                                Text { text: "Exits the JARVIS host process."; font.family: "Consolas"; font.pixelSize: 9; color: "#80C6E5" }
                            }
                            RowLayout {
                                Text { text: "[ Enter ]"; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#00FF9D"; width: 120 }
                                Text { text: "Submits text command from the console box."; font.family: "Consolas"; font.pixelSize: 9; color: "#80C6E5" }
                            }
                            RowLayout {
                                Text { text: "[ Backspace ]"; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#00FF9D"; width: 120 }
                                Text { text: "Clears current active logs when on settings page."; font.family: "Consolas"; font.pixelSize: 9; color: "#80C6E5" }
                            }
                        }

                        Item { Layout.fillHeight: true }
                        
                        Text {
                            text: "Note: Keyboard commands are processed globally within the GUI thread layer, sir."
                            font.family: "Consolas"; font.pixelSize: 8; color: "#507090"; font.italic: true
                        }
                    }
                }

                // Right: Voice & Text Commands Catalog
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 320
                    color: "#08101a"
                    border.color: "#004b73"
                    radius: 4

                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 16; spacing: 12
                        Text { text: "VOICE & CONSOLE COMMANDS"; font.family: JarvisFont.orbitron; font.pixelSize: 11; font.bold: true; color: "#00BFFF" }
                        
                        Rectangle { Layout.fillWidth: true; height: 1; color: "#004b73"; opacity: 0.5 }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            ColumnLayout {
                                spacing: 8
                                width: parent.width

                                Repeater {
                                    model: [
                                        { cmd: "open notepad", desc: "Launch default Windows text editor." },
                                        { cmd: "check cpu status", desc: "Speak out current processor load metrics." },
                                        { cmd: "take screenshot", desc: "Capture system screen and save image." },
                                        { cmd: "volume up / down", desc: "Incrementally change Windows audio volume." },
                                        { cmd: "what is my ip", desc: "Query and show the active network interfaces IP." },
                                        { cmd: "run cyber audit", desc: "Trigger the deep security process scan." },
                                        { cmd: "clear interface logs", desc: "Flushes the HUD command log view." },
                                        { cmd: "shutdown jarvis", desc: "Safely shut down the assistant stack." }
                                    ]

                                    delegate: ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Text {
                                            text: "⚡ \"" + modelData.cmd + "\""
                                            font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#00FF9D"
                                        }
                                        Text {
                                            text: modelData.desc
                                            font.family: "Consolas"; font.pixelSize: 9; color: "#80C6E5"; leftPadding: 14
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Interactive guidelines / operational checklist
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 110
                color: "#08101a"
                border.color: "#004b73"
                radius: 4

                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 8
                    Text { text: "OPERATIONAL STATE GUIDELINES"; font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true; color: "#00BFFF" }
                    Rectangle { Layout.fillWidth: true; height: 1; color: "#004b73"; opacity: 0.5 }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Column {
                            spacing: 4
                            Text { text: "• STANDBY STATE: Waiting for wake word or console command input."; font.family: "Consolas"; font.pixelSize: 8; color: "#80A0C0" }
                            Text { text: "• PROCESSING STATE: Parsing commands through local neural router."; font.family: "Consolas"; font.pixelSize: 8; color: "#80A0C0" }
                        }
                        Column {
                            spacing: 4
                            Text { text: "• SPEAKING STATE: Lip-sync and edge-tts synthesis are currently active."; font.family: "Consolas"; font.pixelSize: 8; color: "#80A0C0" }
                            Text { text: "• SAFE MODE STATUS: Local execution mode when APIs are offline."; font.family: "Consolas"; font.pixelSize: 8; color: "#80A0C0" }
                        }
                    }
                }
            }
        }
    }
}
