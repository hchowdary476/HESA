// SecurityPage.qml — Premium SIEM Dashboard & Cyber Security OS Controls

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: securityRoot

    // Connections to keep track of risk score & security events
    property real riskValue: jarvis.riskScore // bound to riskScore property on JarvisBridge
    property var securityAlerts: []

    Connections {
        target: jarvis
        function onLogReceived(msg, kind) {
            // Filter logs for security, vulnerabilities, or anomalies
            var msgLower = msg.toLowerCase();
            if (msgLower.indexOf("sec") !== -1 || msgLower.indexOf("incident") !== -1 || msgLower.indexOf("vuln") !== -1 || msgLower.indexOf("cve") !== -1 || msgLower.indexOf("process") !== -1 || msgLower.indexOf("alert") !== -1 || msgLower.indexOf("soc") !== -1) {
                var arr = securityRoot.securityAlerts.slice();
                arr.unshift({ text: msg, time: new Date().toLocaleTimeString() });
                if (arr.length > 30) arr = arr.slice(0, 30);
                securityRoot.securityAlerts = arr;
                alertsList.model = securityRoot.securityAlerts;
            }
        }
    }

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: 24
        contentHeight: Math.max(flickable.height, mainLayout.implicitHeight)
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
            id: securityScrollBar
            policy: ScrollBar.AsNeeded
            contentItem: Rectangle {
                implicitWidth: 6
                implicitHeight: 100
                radius: 3
                color: "#00BFFF"
                opacity: securityScrollBar.active ? 0.8 : 0.4
                Behavior on opacity { NumberAnimation { duration: 150 } }
            }
            background: Rectangle {
                implicitWidth: 6
                color: "transparent"
            }
        }

        RowLayout {
            id: mainLayout
            width: flickable.width
            spacing: 20

        // LEFT COLUMN: Controls & SIEM Risk Score
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 2

            // Header block
            Column {
                spacing: 4
                Layout.fillWidth: true
                Text {
                    text: "JARVIS CYBER OS SHIELD"
                    font.family: JarvisFont.orbitron
                    font.pixelSize: 22
                    font.bold: true
                    color: "#00BFFF"
                }
                Text {
                    text: "SECURITY INTRUSION & COMPLIANCE ENGINE"
                    font.family: JarvisFont.orbitron
                    font.pixelSize: 10
                    font.bold: true
                    color: "#00FF9D"
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#004b73"
            }

            // SIEM Risk Level Gauge Panel
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                color: "#08101a"
                border.color: "#004b73"
                border.width: 1
                radius: 6

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 24

                    // Dynamic circular visual gauge
                    Rectangle {
                        width: 120
                        height: 120
                        color: "transparent"
                        border.color: securityRoot.riskValue > 40 ? "#FF4B4B" : (securityRoot.riskValue > 25 ? "#FFB04B" : "#00FF9D")
                        border.width: 4
                        radius: 60
                        Layout.alignment: Qt.AlignVCenter

                        Column {
                            anchors.centerIn: parent
                            spacing: 2
                            Text {
                                text: Math.round(securityRoot.riskValue) + "%"
                                font.family: JarvisFont.orbitron
                                font.pixelSize: 28
                                font.bold: true
                                color: "#FFFFFF"
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text {
                                text: "RISK INDEX"
                                font.family: JarvisFont.orbitron
                                font.pixelSize: 8
                                font.bold: true
                                color: "#80A0C0"
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }
                    }

                    // Risk Details & Compliance Checklist
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Text {
                            text: "OPERATIONAL SECURITY INDEX"
                            font.family: JarvisFont.orbitron
                            font.pixelSize: 12
                            font.bold: true
                            color: "#00BFFF"
                        }

                        Text {
                            text: securityRoot.riskValue > 40 ? "STATUS: CRITICAL THREAT WARNING" : (securityRoot.riskValue > 25 ? "STATUS: INCREASED POSTURE INCIDENTS" : "STATUS: ENFORCED SECURE POSTURE")
                            font.family: JarvisFont.orbitron
                            font.pixelSize: 10
                            font.bold: true
                            color: securityRoot.riskValue > 40 ? "#FF4B4B" : (securityRoot.riskValue > 25 ? "#FFB04B" : "#00FF9D")
                        }

                        Column {
                            spacing: 4
                            Text { text: "• FIREWALL POSTURE: ACTIVE (24 INTRUSIONS BLOCKED)"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#A0C0E0" }
                            Text { text: "• SYMMETRIC API KEY STORAGE: ARMED & AES-ENCRYPTED"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#A0C0E0" }
                            Text { text: "• FILE INTEGRITY MONITORING: VERIFIED (0 INCIDENTS)"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#A0C0E0" }
                        }
                    }
                }
            }

            // Quick Security Actions Control Center
            Text {
                text: "TACTICAL COMMAND ACTIONS"
                font.family: JarvisFont.orbitron
                font.pixelSize: 12
                font.bold: true
                color: "#00BFFF"
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 12
                columnSpacing: 12

                // Button template component inside grid
                Repeater {
                    model: [
                        { label: "LOG CORRELATION AUDIT", cmd: "Jarvis, analyze logs", icon: "📊" },
                        { label: "PROCESS HIJACK AUDIT", cmd: "Jarvis, suspicious process check", icon: "🔍" },
                        { label: "INCIDENT POST-MORTEM TIMELINE", cmd: "Jarvis, create incident timeline", icon: "🕒" },
                        { label: "MITRE ATT&CK COMPARISON", cmd: "Jarvis, compare mitre", icon: "⚔️" },
                        { label: "DAILY SOC REPORT SUMMARIZE", cmd: "Jarvis, prepare daily SOC report", icon: "📋" },
                        { label: "THREAT LANDSCAPE REPORT", cmd: "Jarvis, threat landscape", icon: "🌐" },
                        { label: "COMPTIA SECURITY+ ROADMAP", cmd: "Jarvis, roadmap for security+", icon: "📚" },
                        { label: "COMPTIA SECURITY+ PRACTICE QUIZ", cmd: "Jarvis, prepare me for security plus", icon: "🎯" }
                    ]

                    // Rectangle+MouseArea used instead of native Button to
                    // avoid Qt style customization warnings
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 45
                        color: btnHover.containsMouse ? "#0d2238" : "#08101a"
                        border.color: btnHover.containsMouse ? "#00BFFF" : "#004b73"
                        border.width: 1
                        radius: 4

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8
                            Text {
                                text: modelData.icon
                                font.pixelSize: 14
                            }
                            Text {
                                text: modelData.label
                                font.family: JarvisFont.orbitron
                                font.pixelSize: 9
                                font.bold: true
                                color: "#00FF9D"
                                Layout.fillWidth: true
                            }
                        }

                        MouseArea {
                            id: btnHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: jarvis.submitCommand(modelData.cmd)
                        }
                    }
                }
            }

            Item { Layout.fillHeight: true }
        }

        // RIGHT COLUMN: Active SIEM Audits & Live Security Event Streams
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 1.5
            spacing: 12

            Text {
                text: "LIVE SECURITY SIEM LOG"
                font.family: JarvisFont.orbitron
                font.pixelSize: 12
                font.bold: true
                color: "#00BFFF"
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#050814"
                border.color: "#004b73"
                border.width: 1
                radius: 6
                clip: true

                ListView {
                    id: alertsList
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    model: securityRoot.securityAlerts

                    delegate: Rectangle {
                        width: alertsList.width
                        height: textItem.implicitHeight + 20
                        color: "#08101a"
                        border.color: "#004b73"
                        border.width: 0.5
                        radius: 4

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8
                            Text {
                                text: "⚠️"
                                font.pixelSize: 12
                                Layout.alignment: Qt.AlignTop
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: modelData.time
                                    font.family: JarvisFont.orbitron
                                    font.pixelSize: 8
                                    color: "#80A0C0"
                                }
                                Text {
                                    id: textItem
                                    text: modelData.text
                                    font.family: "Consolas"
                                    font.pixelSize: 9
                                    color: "#E0E0E0"
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
}
