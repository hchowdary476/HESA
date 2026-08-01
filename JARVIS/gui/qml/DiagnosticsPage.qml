// DiagnosticsPage.qml — Runtime health and self-healing diagnostics

import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Item {
    id: diagRoot
    property real cpuPercent: 0
    property real ramPercent: 0
    property int  threadCount: 0

    Connections {
        target: jarvis
        function onMetricsUpdated(cpu, ram, threads, services) {
            diagRoot.cpuPercent  = cpu
            diagRoot.ramPercent  = ram
            diagRoot.threadCount = threads
        }
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
            id: diagScrollBar
            policy: ScrollBar.AsNeeded
            contentItem: Rectangle {
                implicitWidth: 6
                implicitHeight: 100
                radius: 3
                color: "#00BFFF"
                opacity: diagScrollBar.active ? 0.8 : 0.4
                Behavior on opacity { NumberAnimation { duration: 150 } }
            }
            background: Rectangle {
                implicitWidth: 6
                color: "transparent"
            }
        }

        ColumnLayout {
            id: mainCol
            width: parent.width
            spacing: 20

            Text { text: "DIAGNOSTICS CENTER"; font.family: JarvisFont.orbitron; font.pixelSize: 20; font.bold: true; color: "#00BFFF" }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#004b73"; opacity: 0.6 }

            Row {
                spacing: 24
                Repeater {
                    model: [
                        { label: "CPU",     value: Math.round(diagRoot.cpuPercent)  + "%" },
                        { label: "RAM",     value: Math.round(diagRoot.ramPercent)   + "%" },
                        { label: "THREADS", value: diagRoot.threadCount + "" },
                        { label: "STATUS",  value: "HEALTHY" },
                    ]
                    delegate: Rectangle {
                        width: 120; height: 70
                        color: "#08101a"; border.color: "#004b73"; radius: 5
                        Column {
                            anchors.centerIn: parent; spacing: 4
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.label
                                font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.value
                                font.family: JarvisFont.orbitron; font.pixelSize: 18; font.bold: true
                                color: modelData.label === "STATUS" ? "#00FF9D" : "#D6F5FF"
                            }
                        }
                    }
                }
            }

            Text { text: "WINDOWS INTEGRATION HEALTH"; font.family: JarvisFont.orbitron; font.pixelSize: 14; font.bold: true; color: "#00BFFF" }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: healthGrid.implicitHeight + 32
                color: "#08101a"
                border.color: "#004b73"
                radius: 6
                clip: true

                GridLayout {
                    id: healthGrid
                    anchors.fill: parent
                    anchors.margins: 16
                    columns: 2
                    rowSpacing: 10
                    columnSpacing: 30

                    property var healthData: {
                        try {
                            return JSON.parse(jarvis.windowsIntegrationHealth)
                        } catch(e) {
                            return {}
                        }
                    }

                    Connections {
                        target: jarvis
                        function onMetricsUpdated(cpu, ram, threads, services) {
                            try {
                                healthGrid.healthData = JSON.parse(jarvis.windowsIntegrationHealth)
                            } catch(e) {}
                        }
                    }

                    Repeater {
                        model: [
                            { label: "File Explorer Control", key: "file_explorer" },
                            { label: "Browser Control",       key: "browser_control" },
                            { label: "Volume Control",        key: "volume_control" },
                            { label: "Brightness Control",    key: "brightness_control" },
                            { label: "App Launcher",          key: "app_launcher" },
                            { label: "Screenshot Engine",     key: "screenshot_engine" },
                            { label: "Camera Engine",         key: "camera_engine" }
                        ]
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Text {
                                text: modelData.label
                                font.family: "Consolas"
                                font.pixelSize: 10
                                color: "#80C6E5"
                                Layout.preferredWidth: 160
                            }

                            Rectangle {
                                width: 60; height: 20; radius: 3
                                property string statusVal: (healthGrid.healthData && healthGrid.healthData[modelData.key]) || "FAIL"
                                color: statusVal === "PASS" ? "#0c281e" : "#280c10"
                                border.color: statusVal === "PASS" ? "#00FF9D" : "#FF3366"
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: parent.statusVal
                                    font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true
                                    color: parent.statusVal === "PASS" ? "#00FF9D" : "#FF3366"
                                }
                            }
                        }
                    }
                }
            }

            Text { text: "VOICE ENGINE STATUS"; font.family: JarvisFont.orbitron; font.pixelSize: 14; font.bold: true; color: "#00BFFF" }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: voiceGrid.implicitHeight + 32
                color: "#08101a"
                border.color: "#004b73"
                radius: 6
                clip: true

                GridLayout {
                    id: voiceGrid
                    anchors.fill: parent
                    anchors.margins: 16
                    columns: 2
                    rowSpacing: 10
                    columnSpacing: 30

                    // Row 1
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Text {
                            text: "Voice Engine Status"
                            font.family: "Consolas"; font.pixelSize: 10; color: "#80C6E5"
                            Layout.preferredWidth: 160
                        }
                        Rectangle {
                            width: 115; height: 20; radius: 3
                            property string statusVal: jarvis.voiceEngineStatus
                            color: statusVal === "ONLINE" || statusVal === "HEALTHY" || statusVal === "LISTENING" || statusVal === "ACTIVE" ? "#0c281e" : (statusVal === "SPEAKING" ? "#0f223a" : "#280c10")
                            border.color: statusVal === "ONLINE" || statusVal === "HEALTHY" || statusVal === "LISTENING" || statusVal === "ACTIVE" ? "#00FF9D" : (statusVal === "SPEAKING" ? "#00BFFF" : "#FF3366")
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: parent.statusVal
                                font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true
                                color: parent.statusVal === "ONLINE" || parent.statusVal === "HEALTHY" || parent.statusVal === "LISTENING" || parent.statusVal === "ACTIVE" ? "#00FF9D" : (parent.statusVal === "SPEAKING" ? "#00BFFF" : "#FF3366")
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Text {
                            text: "Engine PID"
                            font.family: "Consolas"; font.pixelSize: 10; color: "#80C6E5"
                            Layout.preferredWidth: 160
                        }
                        Rectangle {
                            width: 115; height: 20; radius: 3
                            color: "#0f223a"; border.color: "#00BFFF"; border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: jarvis.voiceEnginePid.toString()
                                font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true; color: "#00BFFF"
                            }
                        }
                    }

                    // Row 2
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Text {
                            text: "Current Speaker"
                            font.family: "Consolas"; font.pixelSize: 10; color: "#80C6E5"
                            Layout.preferredWidth: 160
                        }
                        Rectangle {
                            width: 115; height: 20; radius: 3
                            color: "#0f223a"; border.color: "#00BFFF"; border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: jarvis.voiceCurrentSpeaker
                                font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true; color: "#00BFFF"
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Text {
                            text: "Queue Length"
                            font.family: "Consolas"; font.pixelSize: 10; color: "#80C6E5"
                            Layout.preferredWidth: 160
                        }
                        Rectangle {
                            width: 115; height: 20; radius: 3
                            color: "#0f223a"; border.color: "#00BFFF"; border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: jarvis.voiceQueueLength.toString()
                                font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true; color: "#00BFFF"
                            }
                        }
                    }

                    // Row 3
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Text {
                            text: "Speaking State"
                            font.family: "Consolas"; font.pixelSize: 10; color: "#80C6E5"
                            Layout.preferredWidth: 160
                        }
                        Rectangle {
                            width: 115; height: 20; radius: 3
                            property string statusVal: jarvis.voiceSpeakingState
                            color: statusVal === "SPEAKING" ? "#0f223a" : "#0c281e"
                            border.color: statusVal === "SPEAKING" ? "#00BFFF" : "#00FF9D"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: parent.statusVal
                                font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true
                                color: parent.statusVal === "SPEAKING" ? "#00BFFF" : "#00FF9D"
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Text {
                            text: "Listener State"
                            font.family: "Consolas"; font.pixelSize: 10; color: "#80C6E5"
                            Layout.preferredWidth: 160
                        }
                        Rectangle {
                            width: 115; height: 20; radius: 3
                            property string statusVal: jarvis.voiceListenerState
                            color: statusVal === "ACTIVE" || statusVal === "LISTENING" ? "#0c281e" : "#280c10"
                            border.color: statusVal === "ACTIVE" || statusVal === "LISTENING" ? "#00FF9D" : "#FF3366"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: parent.statusVal
                                font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true
                                color: parent.statusVal === "ACTIVE" || parent.statusVal === "LISTENING" ? "#00FF9D" : "#FF3366"
                            }
                        }
                    }
                }
            }

            Text { text: "SELF-HEALING ENGINE"; font.family: JarvisFont.orbitron; font.pixelSize: 14; font.bold: true; color: "#00BFFF" }

            Repeater {
                model: {
                    try {
                        return JSON.parse(jarvis.selfHealingStatusJson)
                    } catch(e) {
                        return []
                    }
                }
                delegate: Text {
                    text: (modelData.status === "PASS" ? "✅ " : (modelData.status === "WARNING" ? "⚠️ " : "❌ ")) + modelData.name + ": " + modelData.status
                    font.family: "Consolas"
                    font.pixelSize: 10
                    color: modelData.status === "PASS" ? "#00FF9D" : (modelData.status === "WARNING" ? "#FFB800" : "#FF3366")
                }
            }
        }
    }
}
