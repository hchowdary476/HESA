// SettingsPage.qml — Interactive Configuration and system options page

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: settingsRoot

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
            id: settingsScrollBar
            policy: ScrollBar.AsNeeded
            contentItem: Rectangle {
                implicitWidth: 6
                implicitHeight: 100
                radius: 3
                color: "#00BFFF"
                opacity: settingsScrollBar.active ? 0.8 : 0.4
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
            spacing: 20

        // Title
        Column {
            spacing: 2
            Text {
                text: "SYSTEM SETTINGS"
                font.family: JarvisFont.orbitron; font.pixelSize: 22; font.bold: true
                color: "#00BFFF"
            }
            Text {
                text: "CONFIGURATION ENGINE & ENVIRONMENT CONTROLS"
                font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true
                color: "#00FF9D"
            }
        }

        Rectangle { width: 300; height: 1; color: "#004b73"; opacity: 0.6 }

        // Settings Grid
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 300
            color: "#08101a"
            border.color: "#004b73"
            radius: 4

            ColumnLayout {
                anchors.fill: parent; anchors.margins: 18; spacing: 14

                Text { text: "HUD CONFIGURATION PANEL"; font.family: JarvisFont.orbitron; font.pixelSize: 11; font.bold: true; color: "#00BFFF" }
                Rectangle { Layout.fillWidth: true; height: 1; color: "#004b73"; opacity: 0.5 }

                GridLayout {
                    columns: 2
                    rowSpacing: 14
                    columnSpacing: 30
                    Layout.fillWidth: true

                    // 1. AI Provider Selection
                    Text {
                        text: "ACTIVE AI PROVIDER:"
                        font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true
                        color: "#80C6E5"
                    }
                    ComboBox {
                        id: aiProviderCombo
                        width: 220
                        model: ["ChatGPT", "Gemini", "Grok", "Claude", "Ollama"]
                        currentIndex: {
                            var current = jarvis.activeAI || "";
                            if (current.indexOf("ChatGPT") !== -1) return 0;
                            if (current.indexOf("Gemini") !== -1) return 1;
                            if (current.indexOf("Grok") !== -1) return 2;
                            if (current.indexOf("Claude") !== -1) return 3;
                            return 4; // Ollama default
                        }
                        onActivated: {
                            jarvis.setAiProvider(currentText)
                        }
                    }

                    // 2. Speech Rate
                    Text {
                        text: "SPEECH RATE SHIFT:"
                        font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true
                        color: "#80C6E5"
                    }
                    RowLayout {
                        spacing: 10
                        Slider {
                            id: speechRateSlider
                            from: -30; to: 30; value: jarvis.getSpeechRate()
                            stepSize: 2
                            onMoved: jarvis.setSpeechRate(value)
                            Layout.preferredWidth: 200
                        }
                        Text {
                            text: (speechRateSlider.value >= 0 ? "+" : "") + Math.round(speechRateSlider.value) + "%"
                            font.family: "Consolas"; font.pixelSize: 10; color: "#FFFFFF"
                        }
                    }

                    // 3. UI Theme
                    Text {
                        text: "INTERFACE VISUAL THEME:"
                        font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true
                        color: "#80C6E5"
                    }
                    ComboBox {
                        id: themeCombo
                        width: 220
                        model: ["Iron-Man Blue", "Matrix Green", "Dark Knight Black"]
                        currentIndex: 0
                        onActivated: {
                            jarvis.setUiTheme(currentText)
                        }
                    }

                    // 4. Windows Boot Startup
                    Text {
                        text: "LAUNCH AT WINDOWS BOOT:"
                        font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true
                        color: "#80C6E5"
                    }
                    Switch {
                        id: settingsStartupSwitch
                        checked: jarvis.getStartupStatus()
                        onToggled: jarvis.toggleStartup(checked)
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }

        // Action buttons
        Row {
            spacing: 12
            
            Rectangle {
                width: 140; height: 36
                color: restartBtnHover.containsMouse ? "#004b73" : "#0c1826"
                border.color: "#00BFFF"; radius: 3
                Text { anchors.centerIn: parent; text: "RESTART BACKEND"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#00BFFF" }
                MouseArea {
                    id: restartBtnHover; anchors.fill: parent; hoverEnabled: true
                    onClicked: jarvis.restartApp()
                }
            }

            Rectangle {
                width: 140; height: 36
                color: clearBtnHover.containsMouse ? "#004b73" : "#0c1826"
                border.color: "#00BFFF"; radius: 3
                Text { anchors.centerIn: parent; text: "CLEAR INTERFACE LOGS"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#00BFFF" }
                MouseArea {
                    id: clearBtnHover; anchors.fill: parent; hoverEnabled: true
                    onClicked: jarvis.clearLogs()
                }
            }

            Rectangle {
                width: 140; height: 36
                color: exitBtnHover.containsMouse ? "#CC1B1B" : "#400c0c"
                border.color: "#FF4B4B"; radius: 3
                Text { anchors.centerIn: parent; text: "SHUTDOWN SYSTEM"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#FF4B4B" }
                MouseArea {
                    id: exitBtnHover; anchors.fill: parent; hoverEnabled: true
                    onClicked: jarvis.exitApp()
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
}

