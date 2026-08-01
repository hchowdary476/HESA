// CyberSecurityPage.qml — Premium Cyber Security Engine, SOC, & Learning Center
// Holographic Iron-Man style dashboard interface

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: cyberRoot

    property string activeSubTab: "soc" // soc, explorer, learning, compliance, graph
    property real riskValue: jarvis.riskScore
    property var securityAlerts: []
    property string activeQuizAnswer: ""
    property bool showQuizFeedback: false
    property string selectedGraphNode: "Internet Gateway"

    property var currentQuizData: null
    property string userSelectedLetter: ""
    property string socSubTab: "logs" // logs, process

    Connections {
        target: jarvis
        function onLogReceived(msg, kind) {
            var msgLower = msg.toLowerCase();
            // Filter log streams for cyber events
            if (msgLower.indexOf("sec") !== -1 || msgLower.indexOf("incident") !== -1 || 
                msgLower.indexOf("vuln") !== -1 || msgLower.indexOf("cve") !== -1 || 
                msgLower.indexOf("process") !== -1 || msgLower.indexOf("alert") !== -1 || 
                msgLower.indexOf("soc") !== -1 || msgLower.indexOf("threat") !== -1) {
                var arr = cyberRoot.securityAlerts.slice();
                arr.unshift({ text: msg, time: new Date().toLocaleTimeString() });
                if (arr.length > 50) arr = arr.slice(0, 50);
                cyberRoot.securityAlerts = arr;
                alertsList.model = cyberRoot.securityAlerts;
            }
        }
        function onCyberQuizQuestionChanged(jsonStr) {
            try {
                cyberRoot.currentQuizData = JSON.parse(jsonStr)
                cyberRoot.showQuizFeedback = false
                cyberRoot.userSelectedLetter = ""
            } catch(e) {}
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
            id: cyberScrollBar
            policy: ScrollBar.AsNeeded
            contentItem: Rectangle {
                implicitWidth: 6
                implicitHeight: 100
                radius: 3
                color: "#00BFFF"
                opacity: cyberScrollBar.active ? 0.8 : 0.4
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

        // ════════════════════════════════════════════════════════════════════
        // LEFT COLUMN: SUB-TAB NAVIGATION & RISK LEVEL GAUGE
        // ════════════════════════════════════════════════════════════════════
        ColumnLayout {
            id: leftColumnLayout
            Layout.fillHeight: true
            Layout.fillWidth: false
            Layout.preferredWidth: 260
            spacing: 16

            // Section Header
            Column {
                spacing: 2
                Layout.fillWidth: true
                Text {
                    text: "CYBER INTEL CENTER"
                    font.family: JarvisFont.orbitron
                    font.pixelSize: 18
                    font.bold: true
                    color: "#00BFFF"
                }
                Text {
                    text: "MULTI-AI POSTURE MONITOR"
                    font.family: JarvisFont.orbitron
                    font.pixelSize: 9
                    font.bold: true
                    color: "#00FF9D"
                }
            }

            Rectangle {
                Layout.fillWidth: true; height: 1
                color: "#004b73"; opacity: 0.6
            }

            // Sub-navigation List
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Repeater {
                    model: [
                        { label: "🛡️ SOC & THREAT INTEL", key: "soc" },
                        { label: "🔍 CVE & MITRE DISCOVERY", key: "explorer" },
                        { label: "🎓 CERTIFICATION COACH", key: "learning" },
                        { label: "📋 COMPLIANCE & RESEARCH", key: "compliance" },
                        { label: "🕸️ CYBER KNOWLEDGE GRAPH", key: "graph" }
                    ]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        color: cyberRoot.activeSubTab === modelData.key ? "#0d2238" : (tabBtnHover.containsMouse ? "#08101a" : "transparent")
                        border.color: cyberRoot.activeSubTab === modelData.key ? "#00BFFF" : (tabBtnHover.containsMouse ? "#004b73" : "transparent")
                        border.width: 1
                        radius: 4

                        Text {
                            anchors.centerIn: parent
                            text: modelData.label
                            font.family: JarvisFont.orbitron
                            font.pixelSize: 10
                            font.bold: true
                            color: cyberRoot.activeSubTab === modelData.key ? "#D6F5FF" : (tabBtnHover.containsMouse ? "#80C6E5" : "#4D94B3")
                        }

                        MouseArea {
                            id: tabBtnHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: cyberRoot.activeSubTab = modelData.key
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true; height: 1
                color: "#004b73"; opacity: 0.6
            }

            // Risk Gauge Panel
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 190
                color: "#050814"
                border.color: "#004b73"
                border.width: 1
                radius: 6

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14

                    CircleDial {
                        id: riskDial
                        Layout.alignment: Qt.AlignHCenter
                        size: 90
                        value: cyberRoot.riskValue
                    }

                    Text {
                        text: cyberRoot.riskValue > 40 ? "ALERT: POSTURE COMPROMISED" : (cyberRoot.riskValue > 25 ? "WARNING: POTENTIAL HOST HOSTILITY" : "SECURE: OPTIMAL Posture")
                        font.family: JarvisFont.orbitron
                        font.pixelSize: 9
                        font.bold: true
                        color: cyberRoot.riskValue > 40 ? "#FF4B4B" : (cyberRoot.riskValue > 25 ? "#FFB04B" : "#00FF9D")
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Row {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 8
                        Text { text: "FIREWALL: ACTIVE"; font.family: "Consolas"; font.pixelSize: 7; color: "#A0C0E0" }
                        Text { text: "|"; font.family: "Consolas"; font.pixelSize: 7; color: "#406080" }
                        Text { text: "Z-TRUST: ENFORCED"; font.family: "Consolas"; font.pixelSize: 7; color: "#A0C0E0" }
                    }
                }
            }

            // Quick command shortcut button
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                color: quickActHover.containsMouse ? "#CC1B1B" : "#801B1B"
                border.color: "#FF4B4B"
                border.width: 1
                radius: 4

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    Text { text: "🚨"; font.pixelSize: 12 }
                    Text {
                        text: "FORCE SHUT DOWN ALL SHELLS"
                        font.family: JarvisFont.orbitron
                        font.pixelSize: 9
                        font.bold: true
                        color: "white"
                        Layout.fillWidth: true
                    }
                }

                MouseArea {
                    id: quickActHover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        jarvis.submitCommand("Jarvis, terminate all transient shells")
                        jarvis.submitCommand("Jarvis, lock terminal access")
                    }
                }
            }

            Item { Layout.fillHeight: true }
        }

        // Vertical Separator
        Rectangle {
            Layout.fillHeight: true; width: 1
            color: "#004b73"; opacity: 0.6
        }

        // ════════════════════════════════════════════════════════════════════
        // RIGHT MAIN CONTENT WINDOW (Driven by Stack Layout)
        // ════════════════════════════════════════════════════════════════════
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // TAB 1: SOC & THREAT INTEL
            RowLayout {
                anchors.fill: parent
                visible: cyberRoot.activeSubTab === "soc"
                spacing: 16

                // SOC Alert feed & command panel
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1.8
                    spacing: 12

                    SectionHeader { text: "SOC OPERATIONS DASHBOARD" }

                    // Threat metrics cards
                    Row {
                        spacing: 8
                        Layout.fillWidth: true
                        MiniStat { label: "BLOCKED INS"; value: "24" }
                        MiniStat { label: "PORTS OPEN"; value: "3 (SSL/SSH)" }
                        MiniStat { label: "FIM STATUS"; value: "VERIFIED" }
                        MiniStat { label: "C2 DETECTIONS"; value: "0" }
                    }

                    Text {
                        text: "SIEM THREAT FEED"
                        font.family: JarvisFont.orbitron
                        font.pixelSize: 10
                        font.bold: true
                        color: "#00BFFF"
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 120
                        color: "#050814"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 4
                        clip: true

                        ListView {
                            id: alertsList
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 6
                            model: cyberRoot.securityAlerts

                            delegate: Rectangle {
                                width: alertsList.width
                                height: alertText.implicitHeight + 18
                                color: "#08101a"
                                border.color: "#004b73"
                                border.width: 0.5
                                radius: 4

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 8
                                    Text { text: "⚠️"; font.pixelSize: 10; Layout.alignment: Qt.AlignTop }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Text { text: modelData.time; font.family: JarvisFont.orbitron; font.pixelSize: 7; color: "#80A0C0" }
                                        Text {
                                            id: alertText
                                            text: modelData.text
                                            font.family: "Consolas"
                                            font.pixelSize: 8
                                            color: "#FFFFFF"
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Text {
                            text: "CORRELATED AUDIT LOGS"
                            font.family: JarvisFont.orbitron
                            font.pixelSize: 10
                            font.bold: true
                            color: cyberRoot.socSubTab === "logs" ? "#00BFFF" : "#4D94B3"
                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: cyberRoot.socSubTab = "logs"
                            }
                        }
                        Text {
                            text: "|"
                            font.family: JarvisFont.orbitron
                            font.pixelSize: 10
                            color: "#004b73"
                        }
                        Text {
                            text: "PROCESS INTEGRITY AUDIT"
                            font.family: JarvisFont.orbitron
                            font.pixelSize: 10
                            font.bold: true
                            color: cyberRoot.socSubTab === "process" ? "#00BFFF" : "#4D94B3"
                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: cyberRoot.socSubTab = "process"
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#050814"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 4
                        ScrollView {
                            anchors.fill: parent; anchors.margins: 8
                            TextArea {
                                text: cyberRoot.socSubTab === "logs" ? jarvis.cyberLogsAudit : jarvis.cyberProcessAudit
                                font.family: "Consolas"; font.pixelSize: 9
                                color: "#FFFFFF"
                                readOnly: true
                                wrapMode: TextArea.Wrap
                            }
                        }
                    }
                }

                // Cyber Command Shortcuts
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1.2
                    spacing: 12

                    SectionHeader { text: "CYBER SOC COMMANDS" }

                    Text {
                        text: "Submit operational telemetry request, sir."
                        font.family: "Consolas"; font.pixelSize: 9; color: "#80A0C0"
                    }

                    Repeater {
                        model: [
                            { label: "📊 LOG CORRELATION AUDIT", cmd: "Jarvis, analyze security logs" },
                            { label: "🔍 PROCESS HIJACK SCAN", cmd: "Jarvis, suspicious process check" },
                            { label: "📋 EXECUTIVE SOC REPORT", cmd: "Jarvis, generate soc report" },
                            { label: "🕒 INCIDENT POST-MORTEM", cmd: "Jarvis, create incident timeline" },
                            { label: "🌐 GLOBAL THREAT LANDSCAPE", cmd: "Jarvis, threat landscape" },
                            { label: "📡 PACKET CAPTURE DECODER", cmd: "Jarvis, explain packet capture" }
                        ]
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 38
                            color: socBtnHover.containsMouse ? "#0d2238" : "#08101a"
                            border.color: socBtnHover.containsMouse ? "#00BFFF" : "#004b73"
                            border.width: 1
                            radius: 4

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 8
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
                                id: socBtnHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: jarvis.submitCommand(modelData.cmd)
                            }
                        }
                    }
                }
            }

            // TAB 2: CVE & MITRE DISCOVERY
            ColumnLayout {
                anchors.fill: parent
                visible: cyberRoot.activeSubTab === "explorer"
                spacing: 14

                SectionHeader { text: "CVE & MITRE ATT&CK VULNERABILITY ARCHIVE" }

                // Search Bar
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 35
                        color: "#08101a"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 4
                        TextInput {
                            id: cveQueryInput
                            anchors.fill: parent
                            anchors.margins: 10
                            font.family: "Consolas"
                            font.pixelSize: 11
                            color: "white"
                            selectByMouse: true
                            clip: true
                            Text {
                                text: "Enter CVE (e.g. CVE-2021-44228) or MITRE query..."
                                font.family: "Consolas"
                                font.pixelSize: 11
                                color: "#406080"
                                visible: cveQueryInput.text === ""
                            }
                        }
                    }
                    Rectangle {
                        width: 100; height: 35
                        color: searchBtnHover.containsMouse ? "#0d2238" : "#08101a"
                        border.color: "#00BFFF"
                        border.width: 1
                        radius: 4
                        Text {
                            anchors.centerIn: parent
                            text: "SEARCH"
                            font.family: JarvisFont.orbitron
                            font.pixelSize: 10
                            font.bold: true
                            color: "#00BFFF"
                        }
                        MouseArea {
                            id: searchBtnHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (cveQueryInput.text !== "") {
                                    jarvis.submitCommand("Jarvis, explain " + cveQueryInput.text)
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 16

                    // Off-line vulnerability directory
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1.2
                        color: "#050814"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 6
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8
                            Text { text: "POPULAR OFFLINE CVE RECORDS"; font.family: JarvisFont.orbitron; font.pixelSize: 10; color: "#00BFFF" }
                            
                            Repeater {
                                model: [
                                    { id: "CVE-2021-44228", name: "Log4Shell", score: "10.0 (Critical)", desc: "Remote code execution JNDI lookups." },
                                    { id: "CVE-2017-0144", name: "EternalBlue", score: "9.3 (Critical)", desc: "Windows SMBv1 pool corruption overflow." },
                                    { id: "CVE-2014-0160", name: "Heartbleed", score: "7.5 (High)", desc: "OpenSSL heartbeat memory leakage disclosure." }
                                ]
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 50
                                    color: cveItemHover.containsMouse ? "#0d2238" : "#08101a"
                                    border.color: cveItemHover.containsMouse ? "#00BFFF" : "#004b73"
                                    border.width: 0.5
                                    radius: 4
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        spacing: 2
                                        RowLayout {
                                            Text { text: modelData.id + " [" + modelData.name + "]"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#00FF9D" }
                                            Item { Layout.fillWidth: true }
                                            Text { text: "CVSS: " + modelData.score; font.family: "Consolas"; font.pixelSize: 8; color: "#FF4B4B" }
                                        }
                                        Text { text: modelData.desc; font.family: "Consolas"; font.pixelSize: 8; color: "#A0C0E0" }
                                    }
                                    MouseArea {
                                        id: cveItemHover
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: jarvis.submitCommand("Jarvis, explain " + modelData.id)
                                    }
                                }
                            }
                        }
                    }

                    // MITRE techniques
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1.8
                        color: "#050814"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 6
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8
                            Text { text: "MITRE ATT&CK DEFENSIVE STRATEGIES"; font.family: JarvisFont.orbitron; font.pixelSize: 10; color: "#00BFFF" }
                            
                            ScrollView {
                                Layout.fillWidth: true; Layout.preferredHeight: 120
                                ColumnLayout {
                                    width: parent.width; spacing: 8
                                    
                                    Repeater {
                                        model: [
                                            { id: "T1055", label: "Process Injection", desc: "Write executable shells into running process handles.", def: "Monitor VirtualAllocEx/WriteProcessMemory syscall configurations." },
                                            { id: "T1574", label: "Hijack Execution Flow", desc: "DLL hijacking via directory path search order manipulation.", def: "Audit folder file write access; enforce absolute dynamic library linking path dependencies." },
                                            { id: "T1078", label: "Valid Accounts", desc: "Obtain valid active credential assets to gain entry posture.", def: "Implement strictly enforced multi-factor MFA + continuous Zero-Trust access token audits." }
                                        ]
                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 65
                                            color: "#08101a"
                                            border.color: "#004b73"
                                            border.width: 0.5
                                            radius: 4
                                            ColumnLayout {
                                                anchors.fill: parent
                                                anchors.margins: 8
                                                spacing: 2
                                                Text { text: modelData.id + " — " + modelData.label; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#00BFFF" }
                                                Text { text: "• ATTACK: " + modelData.desc; font.family: "Consolas"; font.pixelSize: 8; color: "#FFA6A6" }
                                                Text { text: "• DEFENSE: " + modelData.def; font.family: "Consolas"; font.pixelSize: 8; color: "#C4FFC4" }
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: "#004b73"; opacity: 0.4 }

                            Text { text: "CVE & MALWARE RESEARCH DOSSIER"; font.family: JarvisFont.orbitron; font.pixelSize: 10; color: "#00BFFF" }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                color: "#08101a"
                                border.color: "#004b73"
                                radius: 4
                                ScrollView {
                                    anchors.fill: parent; anchors.margins: 8
                                    TextArea {
                                        text: jarvis.cyberCveExplanation
                                        font.family: "Consolas"; font.pixelSize: 9
                                        color: "#FFFFFF"
                                        readOnly: true
                                        wrapMode: TextArea.Wrap
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // TAB 3: LEARNING CENTER & STUDY ROADMAPS
            RowLayout {
                anchors.fill: parent
                visible: cyberRoot.activeSubTab === "learning"
                spacing: 16

                // Study syllabi
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1.5
                    spacing: 12

                    SectionHeader { text: "CYBER SECURITY ACADEMY" }

                    Text {
                        text: "CERTIFICATION LEARNING SYLLABUS COACH"
                        font.family: JarvisFont.orbitron; font.pixelSize: 10; color: "#00BFFF"
                    }

                    Repeater {
                        model: [
                            { label: "📘 COMPTIA SECURITY+ SYLLABUS", cmd: "Jarvis, learning roadmap for security+" },
                            { label: "📗 CERTIFIED ETHICAL HACKER (CEH)", cmd: "Jarvis, learning roadmap for CEH" },
                            { label: "📙 COMPTIA CySA+ SYLLABUS", cmd: "Jarvis, learning roadmap for CySA+" },
                            { label: "📕 CISSP EXECUTIVE POSTURE", cmd: "Jarvis, learning roadmap for CISSP" }
                        ]
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 38
                            color: certBtnHover.containsMouse ? "#0d2238" : "#08101a"
                            border.color: certBtnHover.containsMouse ? "#00BFFF" : "#004b73"
                            border.width: 1
                            radius: 4
                            Text {
                                anchors.centerIn: parent
                                text: modelData.label
                                font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#D6F5FF"
                            }
                            MouseArea {
                                id: certBtnHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: jarvis.submitCommand(modelData.cmd)
                            }
                        }
                    }

                    // Dynamic Learning Roadmap Output
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#050814"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 6
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6
                            Text { text: "ACTIVE STUDY SYLLABUS & ROADMAP"; font.family: JarvisFont.orbitron; font.pixelSize: 9; color: "#00FF9D" }
                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                color: "#08101a"; border.color: "#004b73"; radius: 4
                                ScrollView {
                                    anchors.fill: parent; anchors.margins: 8
                                    TextArea {
                                        text: jarvis.cyberLearningRoadmap
                                        font.family: "Consolas"; font.pixelSize: 9
                                        color: "#FFFFFF"
                                        readOnly: true
                                        wrapMode: TextArea.Wrap
                                    }
                                }
                            }
                        }
                    }
                }

                // Interactive Practice Quiz
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1.5
                    spacing: 12

                    SectionHeader { text: "INTERACTIVE DRILL COACH" }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#08101a"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 6
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Text {
                                text: "CERTIFICATION TEST PRACTICE"
                                font.family: JarvisFont.orbitron; font.pixelSize: 10; color: "#00BFFF"
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 38
                                color: quizBtn.containsMouse ? "#0d2238" : "#0c1a30"
                                border.color: "#00BFFF"
                                border.width: 1
                                radius: 4
                                Text {
                                    anchors.centerIn: parent
                                    text: "🚀 LOAD PRACTICE QUESTION"
                                    font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#00FF9D"
                                }
                                MouseArea {
                                    id: quizBtn
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        jarvis.submitCommand("Jarvis, prepare me for security+")
                                        cyberRoot.showQuizFeedback = false
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                color: "#050814"
                                border.color: "#004b73"
                                border.width: 0.5
                                radius: 4
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8
                                    Text {
                                        text: "CompTIA Security+ Drill Question:"
                                        font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0"
                                    }
                                    Text {
                                        text: cyberRoot.currentQuizData ? cyberRoot.currentQuizData.question : "Click 'LOAD PRACTICE QUESTION' to begin, sir."
                                        font.family: "Consolas"; font.pixelSize: 9; color: "#FFFFFF"
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }

                                    GridLayout {
                                        columns: 1
                                        Layout.fillWidth: true
                                        rowSpacing: 4; columnSpacing: 6

                                        Repeater {
                                            model: cyberRoot.currentQuizData ? cyberRoot.currentQuizData.options : []
                                            delegate: Rectangle {
                                                id: optionRect
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 28
                                                
                                                property string optionLetter: modelData.charAt(0)
                                                property bool isThisCorrect: optionLetter === (cyberRoot.currentQuizData ? cyberRoot.currentQuizData.answer : "")
                                                property bool isThisSelected: optionLetter === cyberRoot.userSelectedLetter
                                                
                                                color: {
                                                    if (cyberRoot.userSelectedLetter === "") {
                                                        return selectAnsHover.containsMouse ? "#0d2238" : "#0c1a30";
                                                    }
                                                    if (isThisSelected) {
                                                        return isThisCorrect ? "#0c301a" : "#300c0c";
                                                    }
                                                    if (isThisCorrect) {
                                                        return "#0c301a";
                                                    }
                                                    return "#0c1a30";
                                                }
                                                
                                                border.color: {
                                                    if (cyberRoot.userSelectedLetter === "") {
                                                        return selectAnsHover.containsMouse ? "#00BFFF" : "#004b73";
                                                    }
                                                    if (isThisSelected) {
                                                        return isThisCorrect ? "#00FF9D" : "#FF4B4B";
                                                    }
                                                    if (isThisCorrect) {
                                                        return "#00FF9D";
                                                    }
                                                    return "#004b73";
                                                }
                                                border.width: 1
                                                radius: 3
                                                
                                                Text {
                                                    anchors.centerIn: parent
                                                    text: modelData
                                                    font.family: "Consolas"
                                                    font.pixelSize: 9
                                                    font.bold: true
                                                    color: {
                                                        if (cyberRoot.userSelectedLetter === "") {
                                                            return selectAnsHover.containsMouse ? "#D6F5FF" : "#80C6E5";
                                                        }
                                                        if (isThisSelected || isThisCorrect) {
                                                            return "#FFFFFF";
                                                        }
                                                        return "#4D94B3";
                                                    }
                                                    horizontalAlignment: Text.AlignHCenter
                                                }
                                                
                                                MouseArea {
                                                    id: selectAnsHover
                                                    anchors.fill: parent
                                                    hoverEnabled: cyberRoot.userSelectedLetter === ""
                                                    cursorShape: cyberRoot.userSelectedLetter === "" ? Qt.PointingHandCursor : Qt.ArrowCursor
                                                    onClicked: {
                                                        if (cyberRoot.userSelectedLetter !== "") return;
                                                        cyberRoot.userSelectedLetter = optionLetter;
                                                        var isCorrect = isThisCorrect;
                                                        if (isCorrect) {
                                                            cyberRoot.activeQuizAnswer = "CORRECT, sir! " + cyberRoot.currentQuizData.explanation;
                                                        } else {
                                                            cyberRoot.activeQuizAnswer = "INCORRECT, sir. Correct option was " + cyberRoot.currentQuizData.answer + ". " + cyberRoot.currentQuizData.explanation;
                                                        }
                                                        cyberRoot.showQuizFeedback = true
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    Text {
                                        visible: cyberRoot.showQuizFeedback
                                        text: cyberRoot.activeQuizAnswer
                                        font.family: "Consolas"; font.pixelSize: 8; color: cyberRoot.activeQuizAnswer.startsWith("CORRECT") ? "#00FF9D" : "#FF3366"
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // TAB 4: COMPLIANCE & RESEARCH
            RowLayout {
                anchors.fill: parent
                visible: cyberRoot.activeSubTab === "compliance"
                spacing: 16

                // Compliance framework panel
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1.5
                    spacing: 12

                    SectionHeader { text: "COMPLIANCE & GOVERNANCE DASHBOARD" }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#050814"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 6
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8
                            Text { text: "CIS CRITICAL CONTROLS STATUS"; font.family: JarvisFont.orbitron; font.pixelSize: 10; color: "#00BFFF" }
                            
                            Column {
                                spacing: 6
                                width: parent.width
                                Text { text: "✔ CIS 1: Inventory of Enterprise Assets (100%)"; font.family: "Consolas"; font.pixelSize: 9; color: "#00FF9D" }
                                Text { text: "✔ CIS 2: Inventory of Software Assets (100%)"; font.family: "Consolas"; font.pixelSize: 9; color: "#00FF9D" }
                                Text { text: "✔ CIS 3: Data Protection & Key Encryption (80%)"; font.family: "Consolas"; font.pixelSize: 9; color: "#00FF9D" }
                                Text { text: "⚠ CIS 4: Secure Configuration of Assets (WARNING)"; font.family: "Consolas"; font.pixelSize: 9; color: "#FFB04B" }
                                Text { text: "✔ CIS 5: Account Management (90%)"; font.family: "Consolas"; font.pixelSize: 9; color: "#00FF9D" }
                            }

                            Item { width: 1; height: 6 }
                            Text { text: "ISO 27001 ISMS CHECKLIST"; font.family: JarvisFont.orbitron; font.pixelSize: 10; color: "#00BFFF" }
                            Column {
                                spacing: 4
                                Text { text: "• A.12.6.1: Technical Vulnerability Management (COMPLIANT)"; font.family: "Consolas"; font.pixelSize: 8; color: "#A0C0E0" }
                                Text { text: "• A.14.2.1: Secure System Engineering Principles (COMPLIANT)"; font.family: "Consolas"; font.pixelSize: 8; color: "#A0C0E0" }
                                Text { text: "• A.18.1.1: Compliance with Legal Requirements (COMPLIANT)"; font.family: "Consolas"; font.pixelSize: 8; color: "#A0C0E0" }
                            }
                        }
                    }
                }

                // Research papers
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1.5
                    spacing: 12

                    SectionHeader { text: "CYBER SECURITY RESEARCH CENTER" }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        color: "#050814"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 6
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8
                            Text { text: "ACTIVE MULTI-AI INTEL REPORTS"; font.family: JarvisFont.orbitron; font.pixelSize: 10; color: "#00BFFF" }
                            
                            Repeater {
                                model: [
                                    { label: "🛡️ ZERO TRUST DEFENSE PATTERNS", cmd: "Jarvis, review security architecture" },
                                    { label: "🤖 AI PROMPT INJECTION SECURITY AUDIT", cmd: "Jarvis, check prompt security" },
                                    { label: "🌩️ CLOUD CONTAINER PIPELINE SYLLABUS", cmd: "Jarvis, teach cloud security" }
                                ]
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 45
                                    color: resItemHover.containsMouse ? "#0d2238" : "#08101a"
                                    border.color: resItemHover.containsMouse ? "#00BFFF" : "#004b73"
                                    border.width: 0.5
                                    radius: 4
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        Text { text: modelData.label; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#00FF9D" }
                                        Text { text: "Execute research and analysis workflow, sir."; font.family: "Consolas"; font.pixelSize: 8; color: "#A0C0E0" }
                                    }
                                    MouseArea {
                                        id: resItemHover
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: jarvis.submitCommand(modelData.cmd)
                                    }
                                }
                            }
                        }
                    }

                    // Dynamic Compliance & Research Dossier
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#050814"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 6
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 12; spacing: 6
                            Text { text: "RESEARCH DOSSIER & COMPLIANCE OUTPUT"; font.family: JarvisFont.orbitron; font.pixelSize: 9; color: "#00FF9D" }
                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                color: "#08101a"; border.color: "#004b73"; radius: 4
                                ScrollView {
                                    anchors.fill: parent; anchors.margins: 8
                                    TextArea {
                                        text: jarvis.cyberComplianceReport
                                        font.family: "Consolas"; font.pixelSize: 9
                                        color: "#FFFFFF"
                                        readOnly: true
                                        wrapMode: TextArea.Wrap
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // TAB 5: CYBER KNOWLEDGE GRAPH (Interactive network map)
            ColumnLayout {
                anchors.fill: parent
                visible: cyberRoot.activeSubTab === "graph"
                spacing: 12

                SectionHeader { text: "CYBER ATTACK ROADMAP & KNOWLEDGE GRAPH" }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 16

                    // Interactive Graph Canvas
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1.8
                        color: "#050814"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 6
                        clip: true

                        Canvas {
                            id: graphCanvas
                            anchors.fill: parent
                            property string activeNode: cyberRoot.selectedGraphNode

                            onActiveNodeChanged: requestPaint()
                            Component.onCompleted: requestPaint()

                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.clearRect(0, 0, width, height)
                                ctx.save()

                                // Node definitions
                                var nodes = [
                                    { id: "Internet Gateway", x: width * 0.15, y: height * 0.5, type: "gateway", status: "Secure" },
                                    { id: "Firewall Node", x: width * 0.35, y: height * 0.5, type: "fw", status: "Active" },
                                    { id: "Load Balancer", x: width * 0.55, y: height * 0.35, type: "lb", status: "Passing" },
                                    { id: "API Gateway", x: width * 0.55, y: height * 0.65, type: "lb", status: "Secure" },
                                    { id: "Web App Server", x: width * 0.75, y: height * 0.35, type: "app", status: "Patched" },
                                    { id: "Secure DB Subnet", x: width * 0.90, y: height * 0.5, type: "db", status: "Encrypted" }
                                ]

                                // Draw connections
                                ctx.strokeStyle = "#004b73"; ctx.lineWidth = 1.5; ctx.setLineDash([4, 4])
                                function drawConn(n1, n2) {
                                    ctx.beginPath()
                                    ctx.moveTo(n1.x, n1.y)
                                    ctx.lineTo(n2.x, n2.y)
                                    ctx.stroke()
                                }
                                drawConn(nodes[0], nodes[1])
                                drawConn(nodes[1], nodes[2])
                                drawConn(nodes[1], nodes[3])
                                drawConn(nodes[2], nodes[4])
                                drawConn(nodes[3], nodes[5])
                                drawConn(nodes[4], nodes[5])

                                // Draw nodes
                                ctx.setLineDash([])
                                for (var i = 0; i < nodes.length; i++) {
                                    var n = nodes[i]
                                    var isSel = (n.id === cyberRoot.selectedGraphNode)

                                    // Outer glowing ring
                                    if (isSel) {
                                        ctx.strokeStyle = "#00FF9D"
                                        ctx.lineWidth = 3
                                    } else {
                                        ctx.strokeStyle = "#00BFFF"
                                        ctx.lineWidth = 1.5
                                    }
                                    ctx.fillStyle = "#0c1a30"
                                    ctx.beginPath()
                                    ctx.arc(n.x, n.y, 22, 0, Math.PI*2)
                                    ctx.fill()
                                    ctx.stroke()

                                    // Inner circle
                                    ctx.fillStyle = isSel ? "#00FF9D" : "#00BFFF"
                                    ctx.beginPath()
                                    ctx.arc(n.x, n.y, 6, 0, Math.PI*2)
                                    ctx.fill()

                                    // Text label
                                    ctx.fillStyle = "#FFFFFF"
                                    ctx.font = "bold 9px Orbitron"
                                    ctx.textAlign = "center"
                                    ctx.fillText(n.id, n.x, n.y - 28)

                                    // Sub-label status
                                    ctx.fillStyle = isSel ? "#00FF9D" : "#80A0C0"
                                    ctx.font = "8px Consolas"
                                    ctx.fillText(n.status, n.x, n.y + 32)
                                }

                                ctx.restore()
                            }

                            // Handle click detection for nodes
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    var clickX = mouse.x
                                    var clickY = mouse.y
                                    var nodes = [
                                        { id: "Internet Gateway", x: parent.width * 0.15, y: parent.height * 0.5 },
                                        { id: "Firewall Node", x: parent.width * 0.35, y: parent.height * 0.5 },
                                        { id: "Load Balancer", x: parent.width * 0.55, y: parent.height * 0.35 },
                                        { id: "API Gateway", x: parent.width * 0.55, y: parent.height * 0.65 },
                                        { id: "Web App Server", x: parent.width * 0.75, y: parent.height * 0.35 },
                                        { id: "Secure DB Subnet", x: parent.width * 0.90, y: parent.height * 0.5 }
                                    ]

                                    for (var i = 0; i < nodes.length; i++) {
                                        var dist = Math.sqrt(Math.pow(clickX - nodes[i].x, 2) + Math.pow(clickY - nodes[i].y, 2))
                                        if (dist <= 26) {
                                            cyberRoot.selectedGraphNode = nodes[i].id
                                            break
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Selected Node Specs
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1.2
                        color: "#050814"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 6
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8

                            Text {
                                text: "NODE INFORMATION CENTER"
                                font.family: JarvisFont.orbitron; font.pixelSize: 10; color: "#00BFFF"
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 1
                                color: "#004b73"
                            }

                            Text {
                                text: "ACTIVE NODE: " + cyberRoot.selectedGraphNode
                                font.family: JarvisFont.orbitron; font.pixelSize: 11; font.bold: true; color: "#00FF9D"
                            }

                            // Dynamic details based on node selection
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Text {
                                    text: {
                                        if (cyberRoot.selectedGraphNode === "Internet Gateway") {
                                            return "IP ADDRESS: 198.51.100.1\n" +
                                                   "TRAFFIC FILTER: Active DDoS Mitigation\n" +
                                                   "STATUS: Healthy connection stream.\n" +
                                                   "PORT OPEN: 80, 443 only"
                                        } else if (cyberRoot.selectedGraphNode === "Firewall Node") {
                                            return "IPS THREAT ENGINE: Armed\n" +
                                                   "DEEP INSPECTION: Enabled\n" +
                                                   "RULE BASE: Zero-Trust Strict ingress\n" +
                                                   "LOG CORRELATION: Correlating SIEM logs"
                                        } else if (cyberRoot.selectedGraphNode === "Load Balancer") {
                                            return "ALGORITHM: Least Connections\n" +
                                                   "SSL TERMINATION: AES-256 GCM\n" +
                                                   "HEALTH CHECKS: Passing (0 errors)"
                                        } else if (cyberRoot.selectedGraphNode === "API Gateway") {
                                            return "AUTHENTICATION: OAuth 2.0 JWT\n" +
                                                   "RATE LIMITING: 1000 requests/min\n" +
                                                   "THREAT AUDITING: Active scanner"
                                        } else if (cyberRoot.selectedGraphNode === "Web App Server") {
                                            return "OPERATING SYSTEM: Linux Ubuntu\n" +
                                                   "VULNERABILITIES: Patched (No CVEs)\n" +
                                                   "APPLICATION SHIELD: WAF Active\n" +
                                                   "FIM SHA-256 CHECK: Verified"
                                        } else if (cyberRoot.selectedGraphNode === "Secure DB Subnet") {
                                            return "DATABASE TYPE: PostgreSQL\n" +
                                                   "DISK ENCRYPTION: AES-256 XTS\n" +
                                                   "RESTRICTIONS: Enforced secure VPC\n" +
                                                   "MFA ACCESS REQUIREMENT: Enforced"
                                        }
                                        return "No node selected, sir."
                                    }
                                    font.family: "Consolas"
                                    font.pixelSize: 9
                                    color: "#E0E0E0"
                                    wrapMode: Text.Wrap
                                    Layout.fillWidth: true
                                }

                                Rectangle {
                                    Layout.fillWidth: true; height: 1
                                    color: "#004b73"; opacity: 0.5
                                }

                                Text {
                                    text: "To run a diagnostic process scan, speak or submit 'suspicious process check' to audit, sir."
                                    font.family: "Consolas"; font.pixelSize: 8; color: "#80A0C0"; wrapMode: Text.Wrap
                                    Layout.fillWidth: true
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }
                }
            }
        }
    }
}

    // ── Inline helper components ──────────────────────────────────────────

    component SectionHeader: Column {
        property string text: ""
        width: parent.width
        spacing: 4
        Text {
            text: parent.text
            font.family: JarvisFont.orbitron; font.pixelSize: 14; font.bold: true
            color: "#00BFFF"
        }
        Rectangle { width: 180; height: 1; color: "#00BFFF"; opacity: 0.6 }
        Item { width: 1; height: 8 }
    }

    component CircleDial: Item {
        property int   size:  50
        property string label: ""
        property real  value: 0
        width: size; height: size
        Canvas {
            anchors.fill: parent
            property real v: parent.value
            onVChanged: requestPaint()
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.strokeStyle = "#00284d"; ctx.lineWidth = 3
                ctx.beginPath(); ctx.arc(width/2, height/2, width/2 - 6, 0, Math.PI*2); ctx.stroke()
                var ang = (parent.value / 100) * Math.PI * 2
                ctx.strokeStyle = parent.value > 40 ? "#FF4B4B" : (parent.value > 25 ? "#FFB04B" : "#00FF9D")
                ctx.lineWidth = 4
                ctx.beginPath(); ctx.arc(width/2, height/2, width/2 - 6, -Math.PI/2, -Math.PI/2 + ang); ctx.stroke()
                ctx.fillStyle = "#D6F5FF"
                ctx.font = "bold 15px Orbitron"
                ctx.textAlign = "center"; ctx.textBaseline = "middle"
                ctx.fillText(Math.round(parent.value) + "%", width/2, height/2 - 4)
                ctx.fillStyle = "#80A0C0"
                ctx.font = "bold 7px Orbitron"
                ctx.fillText("RISK", width/2, height/2 + 10)
            }
        }
    }

    component MiniStat: Rectangle {
        property string label: ""
        property string value: ""
        width: 100; height: 42
        color: "#08101a"
        border.color: "#004b73"
        border.width: 0.5
        radius: 4
        Column {
            anchors.centerIn: parent
            spacing: 2
            Text { text: label; font.family: "Consolas"; font.pixelSize: 8; color: "#80C6E5"; anchors.horizontalCenter: parent.horizontalCenter }
            Text { text: value; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#FFFFFF"; anchors.horizontalCenter: parent.horizontalCenter }
        }
    }
}
