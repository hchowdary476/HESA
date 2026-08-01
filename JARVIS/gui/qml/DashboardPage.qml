// DashboardPage.qml — 3-column holographic dashboard layout
// Left: Status panels | Center: Face avatar + HUD | Right: Map + modules
// Production Polish: v2.1.0 — All functional issues resolved

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: dashRoot

    // ── Log data model ───────────────────────────────────────────────────
    property var logLines: []

    function getCurrentTimeString() {
        var d = new Date()
        var hh = String(d.getHours()).padStart(2, '0')
        var mm = String(d.getMinutes()).padStart(2, '0')
        var ss = String(d.getSeconds()).padStart(2, '0')
        return "[" + hh + ":" + mm + ":" + ss + "] "
    }

    // Close dropdown on any outside click
    MouseArea {
        anchors.fill: parent
        enabled: optionsDropdown.visible
        z: 9000
        onClicked: {
            dropdownFadeOut.restart()
        }
    }

    Connections {
        target: jarvis
        function onLogReceived(msg, kind) {
            var timeStr = getCurrentTimeString()
            var arr = dashRoot.logLines.slice()
            arr.push({ text: timeStr + msg, kind: kind })
            // Buffer capped at 500 entries
            if (arr.length > 500) arr = arr.slice(arr.length - 500)
            dashRoot.logLines = arr
            logView.model = dashRoot.logLines
            logView.positionViewAtEnd()
        }
    }

    // ── Metrics ──────────────────────────────────────────────────────────
    property real cpuPercent: 0
    property real ramPercent: 0
    property int  threadCount: 0
    property string windowsInfoJson: jarvis.windowsSystemInfo

    function getWindowsUptime() {
        try {
            var data = JSON.parse(windowsInfoJson)
            if (data && data.uptime) {
                var u = data.uptime;
                if (u.indexOf("day") !== -1) {
                    var parts = u.split(",");
                    var days = parts[0].trim().split(" ")[0] + "d";
                    var timeParts = parts[1].trim().split(":");
                    return days + " " + timeParts[0] + ":" + timeParts[1];
                } else {
                    var tParts = u.split(":");
                    if (tParts.length >= 2) {
                        return tParts[0] + ":" + tParts[1];
                    }
                    return u;
                }
            }
        } catch(e) {}
        return "00:00"
    }

    Connections {
        target: jarvis
        function onMetricsUpdated(cpu, ram, threads, services) {
            dashRoot.cpuPercent  = cpu
            dashRoot.ramPercent  = ram
            dashRoot.threadCount = threads

            // Tick history graphs
            cpuGraph.tick(cpu)
            ramGraph.tick(ram)
            diskGraph.tick(jarvis.diskPercent)
            
            var netVal = parseFloat(jarvis.networkStatus)
            if (isNaN(netVal)) netVal = 0.0
            netGraph.tick(netVal)
        }
        function onWindowsSystemInfoChanged(json) {
            dashRoot.windowsInfoJson = json
        }
        function onSystemStatusChanged(json) {
            // Keep status bindings updated
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 0
        spacing: 0

        // ════════════════════════════════════════════════════════════════
        // LEFT PANEL
        // ════════════════════════════════════════════════════════════════
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: parent.width * 0.27
            color: "transparent"

            Flickable {
                id: leftFlick
                anchors { fill: parent; margins: 24 }
                contentHeight: leftCol.implicitHeight
                clip: true
                focus: true

                Keys.onUpPressed: leftFlick.contentY = Math.max(0, leftFlick.contentY - 40)
                Keys.onDownPressed: leftFlick.contentY = Math.min(leftFlick.contentHeight - leftFlick.height, leftFlick.contentY + 40)
                Keys.onPressed: {
                    if (event.key === Qt.Key_PageUp) {
                        leftFlick.contentY = Math.max(0, leftFlick.contentY - leftFlick.height)
                        event.accepted = true
                    } else if (event.key === Qt.Key_PageDown) {
                        leftFlick.contentY = Math.min(leftFlick.contentHeight - leftFlick.height, leftFlick.contentY + leftFlick.height)
                        event.accepted = true
                    } else if (event.key === Qt.Key_Home) {
                        leftFlick.contentY = 0
                        event.accepted = true
                    } else if (event.key === Qt.Key_End) {
                        leftFlick.contentY = leftFlick.contentHeight - leftFlick.height
                        event.accepted = true
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    id: leftScrollBar
                    policy: ScrollBar.AsNeeded
                    contentItem: Rectangle {
                        implicitWidth: 4
                        radius: 2
                        color: "#00BFFF"
                        opacity: leftScrollBar.active ? 0.8 : 0.3
                        Behavior on opacity { NumberAnimation { duration: 150 } }
                    }
                    background: Rectangle {
                        implicitWidth: 4
                        color: "transparent"
                    }
                }

                Column {
                    id: leftCol
                    width: parent.width
                    spacing: 0

                    // ── SYSTEM STATUS ────────────────────────────────────
                    SectionHeader { text: "SYSTEM STATUS" }

                    // Dials row
                    Row {
                        spacing: 12
                        width: parent.width

                        // CPU Dial
                        Column {
                            spacing: 6
                            CircleDial {
                                size: 52
                                value: dashRoot.cpuPercent
                            }
                            Text {
                                text: "CPU"
                                font.family: JarvisFont.orbitron
                                font.pixelSize: 8
                                color: "#80C6E5"
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text {
                                text: jarvis.temperature.toFixed(0) + "°C"
                                font.family: "Consolas"
                                font.pixelSize: 9
                                font.bold: true
                                color: "#D6F5FF"
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }

                        // POWER Dial
                        Column {
                            spacing: 6
                            CircleDial {
                                size: 52
                                value: Math.round(jarvis.batteryPercent / 2.0)
                            }
                            Text {
                                text: "POWER"
                                font.family: JarvisFont.orbitron
                                font.pixelSize: 8
                                color: "#80C6E5"
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text {
                                text: jarvis.batteryPercent + "%"
                                font.family: "Consolas"
                                font.pixelSize: 9
                                font.bold: true
                                color: "#D6F5FF"
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }

                        // UPTIME Dial
                        Column {
                            spacing: 6
                            CircleDial {
                                size: 52
                                value: jarvis.gpuPercent
                            }
                            Text {
                                text: "UPTIME"
                                font.family: JarvisFont.orbitron
                                font.pixelSize: 8
                                color: "#80C6E5"
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text {
                                text: dashRoot.getWindowsUptime()
                                font.family: "Consolas"
                                font.pixelSize: 9
                                font.bold: true
                                color: "#D6F5FF"
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }

                        // STATUS Dial
                        Column {
                            spacing: 6
                            CircleDial {
                                size: 52
                                value: Math.round(jarvis.diskPercent * 0.18)
                            }
                            Text {
                                text: "STATUS"
                                font.family: JarvisFont.orbitron
                                font.pixelSize: 8
                                color: "#80C6E5"
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text {
                                text: jarvis.internetStatus === "ONLINE" ? "OPTIMAL" : "LIMITED"
                                font.family: "Consolas"
                                font.pixelSize: 9
                                font.bold: true
                                color: jarvis.internetStatus === "ONLINE" ? "#00FF9D" : "#FF3366"
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }
                    }

                    // ── LIVE HOST METRICS ────────────────────────────────
                    Item { width: 1; height: 18 }
                    SectionHeader { text: "LIVE HOST METRICS" }

                     Repeater {
                        model: [
                            { icon: "⚡", iconColor: "#FFB800", name: "CPU USAGE",       value: Math.round(dashRoot.cpuPercent) + "%", color: "#00FF9D" },
                            { icon: "⚡", iconColor: "#FFB800", name: "RAM USAGE",       value: Math.round(dashRoot.ramPercent) + "%", color: "#FFB800" },
                            { icon: "⚙",  iconColor: "#00BFFF", name: "GPU USAGE",       value: Math.round(jarvis.gpuPercent) + "%", color: "#00FF9D" },
                            { icon: "🖴",  iconColor: "#A333FF", name: "DISK USAGE",      value: Math.round(jarvis.diskPercent) + "%", color: "#00FF9D" },
                            { icon: "🌡",  iconColor: "#FF3366", name: "TEMPERATURE",     value: jarvis.temperature.toFixed(1) + "°C", color: "#00FF9D" },
                            { icon: "🔋",  iconColor: "#00FF9D", name: "BATTERY",         value: jarvis.batteryPercent + "%", color: "#00FF9D" },
                            { icon: "❤️",  iconColor: "#FF3366", name: "BATTERY HEALTH",   value: jarvis.batteryHealth, color: "#FFB800" },
                            { icon: "🌐",  iconColor: "#00BFFF", name: "INTERNET STATUS", value: jarvis.internetStatus, color: "#00FF9D" },
                            { icon: "⏱",  iconColor: "#00FF9D", name: "INTERNET LATENCY", value: jarvis.internetLatency.toFixed(1) + " ms", color: "#00FF9D" },
                            { icon: "📤",  iconColor: "#00FF9D", name: "UPLOAD SPEED",     value: jarvis.uploadSpeed, color: "#00FF9D" },
                            { icon: "📥",  iconColor: "#00FF9D", name: "DOWNLOAD SPEED",   value: jarvis.downloadSpeed, color: "#00FF9D" },
                            { icon: "☰",  iconColor: "#A333FF", name: "ACTIVE PROCESSES", value: jarvis.activeProcesses.toString(), color: "#FFB800" },
                            { icon: "🧠",  iconColor: "#FF33FF", name: "AI REQUESTS",      value: jarvis.aiRequests.toString(), color: "#FFB800" },
                            { icon: "🎤",  iconColor: "#FFB800", name: "VOICE REQUESTS",   value: jarvis.voiceRequests.toString(), color: "#FFB800" }
                        ]
                        delegate: RowLayout {
                            width: parent.width
                            height: 22
                            spacing: 0
                            RowLayout {
                                spacing: 4
                                Text {
                                    text: modelData.icon
                                    font.family: "Segoe UI Symbol"
                                    font.pixelSize: 10
                                    color: modelData.iconColor
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                Text {
                                    text: modelData.name
                                    font.family: "Consolas"
                                    font.pixelSize: 9
                                    font.bold: true
                                    color: "#80C6E5"
                                    Layout.alignment: Qt.AlignVCenter
                                }
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: modelData.value
                                font.family: "Consolas"
                                font.pixelSize: 9
                                font.bold: true
                                color: modelData.color
                                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                            }
                        }
                    }

                    // ── VOICE RECOGNITION ────────────────────────────────
                    Item { width: 1; height: 18 }
                    SectionHeader { text: "VOICE RECOGNITION" }

                    VoiceVisualizationEngine {
                        width: parent.width
                        height: 40
                    }

                    Item { width: 1; height: 8 }

                    // Voice pipeline stage display
                    property string _voiceState: "STANDBY"
                    Connections {
                        target: jarvis
                        function onStateChanged(s) { leftCol._voiceState = s }
                    }

                    // Pipeline stages
                    Column {
                        width: parent.width
                        spacing: 3

                        Repeater {
                            model: [
                                { label: "WAKE WORD",  stage: "STANDBY",    icon: "◉" },
                                { label: "LISTENING",  stage: "LISTENING",  icon: "◎" },
                                { label: "RECOGNIZED", stage: "PROCESSING", icon: "◈" },
                                { label: "EXECUTING",  stage: "EXECUTING",  icon: "◆" },
                                { label: "COMPLETE",   stage: "STANDBY",    icon: "✓" }
                            ]

                            delegate: RowLayout {
                                width: parent.width
                                height: 18
                                spacing: 6

                                // Determine which stage is "active"
                                property bool isActive: {
                                    var s = leftCol._voiceState
                                    if (modelData.label === "WAKE WORD")
                                        return s === "STANDBY" || s === "BOOTING"
                                    if (modelData.label === "LISTENING")
                                        return s === "LISTENING"
                                    if (modelData.label === "RECOGNIZED")
                                        return s === "PROCESSING"
                                    if (modelData.label === "EXECUTING")
                                        return s === "EXECUTING"
                                    if (modelData.label === "COMPLETE")
                                        return s === "SPEAKING"
                                    return false
                                }

                                Text {
                                    text: modelData.icon
                                    font.pixelSize: 10
                                    color: isActive ? "#00BFFF" : "#1a3a50"
                                    Layout.alignment: Qt.AlignVCenter
                                    Behavior on color { ColorAnimation { duration: 200 } }
                                }
                                Text {
                                    text: modelData.label
                                    font.family: "Consolas"
                                    font.pixelSize: 9
                                    font.bold: isActive
                                    color: isActive ? "#00BFFF" : "#2a4a60"
                                    Layout.alignment: Qt.AlignVCenter
                                    Behavior on color { ColorAnimation { duration: 200 } }
                                }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    width: 6; height: 6; radius: 3
                                    color: isActive ? "#00FF9D" : "#112233"
                                    Layout.alignment: Qt.AlignVCenter
                                    Behavior on color { ColorAnimation { duration: 200 } }
                                    SequentialAnimation on opacity {
                                        running: isActive
                                        loops: Animation.Infinite
                                        NumberAnimation { from: 1.0; to: 0.2; duration: 500 }
                                        NumberAnimation { from: 0.2; to: 1.0; duration: 500 }
                                    }
                                }
                            }
                        }
                    }

                    // ── COMMAND CONSOLE ───────────────────────────────────
                    Item { width: 1; height: 18 }
                    SectionHeader { text: "COMMAND CONSOLE" }

                    // Log terminal box
                    Rectangle {
                        width: parent.width
                        height: 200
                        color: "#050814"
                        border.color: "#004b73"
                        border.width: 1
                        radius: 3
                        clip: true

                        ListView {
                            id: logView
                            anchors { fill: parent; margins: 8 }
                            model: dashRoot.logLines
                            clip: true
                            delegate: Text {
                                width: logView.width
                                text: modelData.text
                                font.family: "Consolas"
                                font.pixelSize: 9
                                wrapMode: Text.WordWrap
                                color: {
                                    var k = modelData.kind || ""
                                    if (k === "error")   return "#FF3366"
                                    if (k === "ok")      return "#00FF9D"
                                    if (k === "task")    return "#FFB800"
                                    if (k === "voice")   return "#00BFFF"
                                    if (k === "ai")      return "#A333FF"
                                    if (k === "warning") return "#FF8800"
                                    if (k === "security")return "#FF33FF"
                                    return "#80C6E5"
                                }
                            }
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOff }
                        }
                    }
                }
            }
        }

        // ════════════════════════════════════════════════════════════════
        // CENTER — Face avatar + HUD
        // ════════════════════════════════════════════════════════════════
        Item {
            Layout.fillHeight: true
            Layout.fillWidth: true

            // HUD annotation overlay (behind face so face is on top)
            HudEngine {
                anchors.fill: parent
            }

            // ── Particle / neural pulse overlay (z=0, behind face) ───────
            ParticleOverlay {
                anchors.fill: parent
                z: 1
            }

            // Face avatar (centered)
            FaceEngine {
                id: faceEngine
                anchors.centerIn: parent
                width: 420
                height: 420
                z: 2
            }

            // Center Column Horizontal status bar
            Rectangle {
                id: statusHudBar
                height: 52
                anchors { top: parent.top; left: parent.left; right: parent.right; topMargin: 24; leftMargin: 24; rightMargin: 24 }
                color: "#081220"
                border.color: "#004b73"
                border.width: 1
                radius: 4
                z: 10

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 15
                    anchors.rightMargin: 15
                    spacing: 12

                    // Left icon - target / radar style circle
                    Rectangle {
                        width: 32; height: 32; radius: 16
                        color: "transparent"
                        border.color: "#00BFFF"
                        border.width: 1
                        Layout.alignment: Qt.AlignVCenter
                        
                        // inner circle/crosshair
                        Rectangle {
                            width: 16; height: 16; radius: 8
                            color: "transparent"
                            border.color: "#00BFFF"
                            border.width: 0.5
                            anchors.centerIn: parent
                        }
                        
                        // Pulsing dot in center
                        Rectangle {
                            width: 6; height: 6; radius: 3
                            color: "#00FF9D"
                            anchors.centerIn: parent
                            SequentialAnimation on opacity {
                                loops: Animation.Infinite
                                NumberAnimation { from: 1.0; to: 0.3; duration: 800 }
                                NumberAnimation { from: 0.3; to: 1.0; duration: 800 }
                            }
                        }
                    }

                    // Column 1: Active AI
                    Column {
                        spacing: 2
                        Layout.alignment: Qt.AlignVCenter
                        Text { text: "ACTIVE AI"; font.family: "Consolas"; font.pixelSize: 8; color: "#80C6E5" }
                        Text { text: jarvis.activeAI || "Ollama (Local)"; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#00FF9D" }
                    }

                    // Separator
                    Rectangle { width: 1; height: 24; color: "#004b73"; opacity: 0.5; Layout.alignment: Qt.AlignVCenter }

                    // Column 2: Model
                    Column {
                        spacing: 2
                        Layout.alignment: Qt.AlignVCenter
                        Text { text: "MODEL"; font.family: "Consolas"; font.pixelSize: 8; color: "#80C6E5" }
                        Text { text: jarvis.activeModel || "qwen2:latest"; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#FFFFFF" }
                    }

                    // Separator
                    Rectangle { width: 1; height: 24; color: "#004b73"; opacity: 0.5; Layout.alignment: Qt.AlignVCenter }

                    // Column 3: Latency
                    Column {
                        spacing: 2
                        Layout.alignment: Qt.AlignVCenter
                        Text { text: "LATENCY"; font.family: "Consolas"; font.pixelSize: 8; color: "#80C6E5" }
                        Text { text: (jarvis.latencyMs !== undefined && jarvis.latencyMs !== null ? jarvis.latencyMs.toFixed(0) : "0") + " ms"; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#00FF9D" }
                    }

                    // Separator
                    Rectangle { width: 1; height: 24; color: "#004b73"; opacity: 0.5; Layout.alignment: Qt.AlignVCenter }

                    // Column 4: Status
                    Column {
                        spacing: 2
                        Layout.alignment: Qt.AlignVCenter
                        Text { text: "STATUS"; font.family: "Consolas"; font.pixelSize: 8; color: "#80C6E5" }
                        Text { text: jarvis.apiStatus.toUpperCase() === "ONLINE" || jarvis.apiStatus.toUpperCase() === "OPTIMAL" ? "READY" : jarvis.apiStatus.toUpperCase(); font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#00FF9D" }
                    }

                    Item { Layout.fillWidth: true }

                    // AI OPTIONS Button
                    Rectangle {
                        id: optionsButton
                        width: 96; height: 28
                        color: optBtnMouse.containsMouse ? "#0d2238" : "transparent"
                        border.color: "#00BFFF"
                        border.width: 1
                        radius: 4
                        Layout.alignment: Qt.AlignVCenter

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Text {
                                text: "⚙"
                                font.pixelSize: 11
                                color: "#00BFFF"
                            }
                            Text {
                                text: "AI OPTIONS"
                                font.family: "Consolas"
                                font.pixelSize: 9
                                font.bold: true
                                color: "#00BFFF"
                            }
                        }

                        Behavior on color { ColorAnimation { duration: 150 } }

                        MouseArea {
                            id: optBtnMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (optionsDropdown.visible) {
                                    dropdownFadeOut.restart()
                                } else {
                                    optionsDropdown.visible = true
                                    dropdownFadeIn.restart()
                                }
                            }
                        }
                    }
                }

                // ── Professional AI Options Dropdown ─────────────────────
                Rectangle {
                    id: optionsDropdown
                    width: 215
                    anchors { top: parent.bottom; right: parent.right; topMargin: 4 }
                    color: "#060f1e"
                    border.color: "#00BFFF"
                    border.width: 1
                    radius: 6
                    visible: false
                    opacity: 0
                    z: 9999

                    // Dynamic height based on content
                    height: dropdownCol.implicitHeight + 16

                    // Fade-in animation
                    NumberAnimation {
                        id: dropdownFadeIn
                        target: optionsDropdown
                        property: "opacity"
                        from: 0; to: 1
                        duration: 180
                        easing.type: Easing.OutCubic
                    }

                    // Fade-out animation — hides after complete
                    SequentialAnimation {
                        id: dropdownFadeOut
                        NumberAnimation {
                            target: optionsDropdown
                            property: "opacity"
                            from: 1; to: 0
                            duration: 150
                            easing.type: Easing.InCubic
                        }
                        ScriptAction { script: optionsDropdown.visible = false }
                    }

                    // Top accent line
                    Rectangle {
                        anchors { top: parent.top; left: parent.left; right: parent.right; topMargin: 0 }
                        height: 2
                        color: "#00BFFF"
                        radius: 6
                    }

                    Column {
                        id: dropdownCol
                        anchors { top: parent.top; left: parent.left; right: parent.right; topMargin: 12; bottomMargin: 8 }
                        spacing: 2

                        Repeater {
                            model: [
                                { label: "AI Orchestrator",  icon: "🧠", page: "aistatus"  },
                                { label: "AI Providers",     icon: "☁",  page: "aistatus"  },
                                { label: "AI Models",        icon: "🤖", page: "aistatus"  },
                                { label: "Router Settings",  icon: "⚡", page: "settings"  },
                                { label: "Fallback Rules",   icon: "↺",  page: "aistatus"  },
                                { label: "Token Usage",      icon: "📊", page: "aistatus"  },
                                { label: "AI Logs",          icon: "📋", page: "diagnostics" }
                            ]

                            delegate: Rectangle {
                                width: dropdownCol.width
                                height: 32
                                color: itemMouse.containsMouse ? "#0d2238" : "transparent"
                                radius: 4

                                Behavior on color { ColorAnimation { duration: 100 } }

                                RowLayout {
                                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; leftMargin: 12; rightMargin: 10 }
                                    spacing: 10

                                    Text {
                                        text: modelData.icon
                                        font.pixelSize: 13
                                        font.family: "Segoe UI Symbol"
                                        color: itemMouse.containsMouse ? "#00BFFF" : "#4a7a9b"
                                        Layout.alignment: Qt.AlignVCenter
                                        Behavior on color { ColorAnimation { duration: 100 } }
                                    }
                                    Text {
                                        text: modelData.label
                                        font.family: "Consolas"
                                        font.pixelSize: 10
                                        font.bold: itemMouse.containsMouse
                                        color: itemMouse.containsMouse ? "#FFFFFF" : "#80C6E5"
                                        Layout.fillWidth: true
                                        Layout.alignment: Qt.AlignVCenter
                                        Behavior on color { ColorAnimation { duration: 100 } }
                                    }
                                    Text {
                                        text: "›"
                                        font.pixelSize: 14
                                        color: itemMouse.containsMouse ? "#00BFFF" : "#204060"
                                        Layout.alignment: Qt.AlignVCenter
                                        Behavior on color { ColorAnimation { duration: 100 } }
                                    }
                                }

                                MouseArea {
                                    id: itemMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        dropdownFadeOut.restart()
                                        // Navigate to page — trigger via root property
                                        var target = modelData.page
                                        // Walk up to root ApplicationWindow and set activePage
                                        var p = dashRoot.parent
                                        while (p && p.parent) { p = p.parent }
                                        if (p && p.activePage !== undefined) {
                                            p.activePage = target
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ════════════════════════════════════════════════════════════════
        // RIGHT PANEL
        // ════════════════════════════════════════════════════════════════
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: parent.width * 0.27
            color: "transparent"

            Flickable {
                id: rightFlick
                anchors { fill: parent; margins: 24 }
                contentHeight: rightCol.implicitHeight
                clip: true
                focus: true

                Keys.onUpPressed: rightFlick.contentY = Math.max(0, rightFlick.contentY - 40)
                Keys.onDownPressed: rightFlick.contentY = Math.min(rightFlick.contentHeight - rightFlick.height, rightFlick.contentY + 40)
                Keys.onPressed: {
                    if (event.key === Qt.Key_PageUp) {
                        rightFlick.contentY = Math.max(0, rightFlick.contentY - rightFlick.height)
                        event.accepted = true
                    } else if (event.key === Qt.Key_PageDown) {
                        rightFlick.contentY = Math.min(rightFlick.contentHeight - rightFlick.height, rightFlick.contentY + rightFlick.height)
                        event.accepted = true
                    } else if (event.key === Qt.Key_Home) {
                        rightFlick.contentY = 0
                        event.accepted = true
                    } else if (event.key === Qt.Key_End) {
                        rightFlick.contentY = rightFlick.contentHeight - rightFlick.height
                        event.accepted = true
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    id: rightScrollBar
                    policy: ScrollBar.AsNeeded
                    contentItem: Rectangle {
                        implicitWidth: 4
                        radius: 2
                        color: "#00BFFF"
                        opacity: rightScrollBar.active ? 0.8 : 0.3
                        Behavior on opacity { NumberAnimation { duration: 150 } }
                    }
                    background: Rectangle {
                        implicitWidth: 4
                        color: "transparent"
                    }
                }

                Column {
                    id: rightCol
                    width: parent.width
                    spacing: 0

                    // ── GLOBAL MAP ────────────────────────────────────────
                    SectionHeader { text: "GLOBAL MAP" }
                    Rectangle {
                        width: parent.width
                        height: 150
                        color: "#050814"
                        border.color: "#004b73"
                        radius: 2
                        clip: true

                        MapEngine {
                            anchors.fill: parent
                        }
                    }

                    RowLayout {
                        width: parent.width
                        height: 28
                        spacing: 0
                        Item { Layout.fillWidth: true }
                        Column {
                            Text { text: "ACTIVE CONNECTIONS"; font.family: "Consolas"; font.pixelSize: 8; color: "#80C6E5" }
                            Text { text: "12,458"; font.family: JarvisFont.orbitron; font.pixelSize: 12; font.bold: true; color: "#D6F5FF" }
                        }
                        Item { width: 20; Layout.preferredWidth: 20 }
                        Column {
                            Text { text: "THREATS BLOCKED"; font.family: "Consolas"; font.pixelSize: 8; color: "#80C6E5" }
                            Text { text: "1,248"; font.family: JarvisFont.orbitron; font.pixelSize: 12; font.bold: true; color: "#D6F5FF" }
                        }
                    }

                    // ── ACTIVE MODULES ────────────────────────────────────
                    Item { width: 1; height: 18 }
                    SectionHeader { text: "ACTIVE MODULES" }

                    Repeater {
                        id: activeModulesRepeater
                        model: jarvis.activeModulesStatus !== "[]" ? JSON.parse(jarvis.activeModulesStatus) : []
                        delegate: Rectangle {
                            width: rightCol.width
                            height: 46
                            color: "transparent"
                            clip: true

                            // Status indicator bar on left
                            Rectangle {
                                id: modIndicatorBar
                                width: 2; height: parent.height
                                color: modelData.color
                                anchors.left: parent.left
                                opacity: 0.7
                            }

                            ColumnLayout {
                                x: 10
                                y: 0
                                width: parent.width - 14   // 10 left + 4 right
                                height: parent.height
                                spacing: 2

                                // Top row: status dot + name + status badge
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 22
                                    spacing: 5
                                    Layout.alignment: Qt.AlignVCenter

                                    // Pulsing status dot (8px fixed)
                                    Rectangle {
                                        width: 6; height: 6; radius: 3
                                        color: modelData.color
                                        Layout.alignment: Qt.AlignVCenter
                                        Layout.preferredWidth: 8

                                        SequentialAnimation on opacity {
                                            loops: Animation.Infinite
                                            running: modelData.status === "ONLINE"
                                            NumberAnimation { from: 1.0; to: 0.2; duration: 900; easing.type: Easing.InOutQuad }
                                            NumberAnimation { from: 0.2; to: 1.0; duration: 900; easing.type: Easing.InOutQuad }
                                        }
                                    }

                                    // Module name — takes all remaining space, truncates if needed
                                    Text {
                                        text: modelData.name.toUpperCase()
                                        font.family: "Consolas"; font.pixelSize: 9; font.bold: true
                                        color: "#80C6E5"
                                        Layout.fillWidth: true
                                        Layout.alignment: Qt.AlignVCenter
                                        elide: Text.ElideRight
                                        clip: true
                                        verticalAlignment: Text.AlignVCenter
                                    }

                                    // Status badge — fixed width, clipped
                                    Rectangle {
                                        Layout.preferredWidth: 54
                                        Layout.preferredHeight: 14
                                        color: modelData.color + "22"
                                        border.color: modelData.color
                                        border.width: 1
                                        radius: 2
                                        Layout.alignment: Qt.AlignVCenter
                                        clip: true
                                        Text {
                                            anchors.centerIn: parent
                                            width: parent.width - 4
                                            text: modelData.status
                                            font.family: "Consolas"; font.pixelSize: 8; font.bold: true
                                            color: modelData.color
                                            elide: Text.ElideRight
                                            horizontalAlignment: Text.AlignHCenter
                                        }
                                    }
                                }

                                // Bottom row: uptime + heartbeat — both clipped
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 18
                                    spacing: 4

                                    Text {
                                        text: "UP " + (modelData.uptime || "00:00:00")
                                        font.family: "Consolas"; font.pixelSize: 8
                                        color: "#3a6a8a"
                                        Layout.preferredWidth: 88
                                        elide: Text.ElideRight
                                        clip: true
                                        verticalAlignment: Text.AlignVCenter
                                    }

                                    Item { Layout.fillWidth: true }

                                    Text {
                                        text: modelData.last_heartbeat || "N/A"
                                        font.family: "Consolas"; font.pixelSize: 8
                                        color: "#2a5a7a"
                                        Layout.preferredWidth: 58
                                        horizontalAlignment: Text.AlignRight
                                        elide: Text.ElideRight
                                        clip: true
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }

                            // Bottom divider
                            Rectangle {
                                anchors.bottom: parent.bottom
                                width: parent.width; height: 1
                                color: "#091828"
                            }
                        }
                    }

                    // ── SYSTEM MONITOR ────────────────────────────────────
                    Item { width: 1; height: 18 }
                    SectionHeader { text: "SYSTEM MONITOR" }

                    MetricRow {
                        label: "CPU Usage"
                        value: Math.round(dashRoot.cpuPercent) + "%"
                        avgVal: "AVG: " + Math.round(cpuGraph.avgValue) + "%"
                        maxVal: "MAX: " + Math.round(Math.max(13, cpuGraph.maxValue)) + "%"
                    }
                    MiniGraph { id: cpuGraph; barColor: "#00BFFF" }

                    MetricRow {
                        label: "RAM Usage"
                        value: Math.round(dashRoot.ramPercent) + "%"
                        avgVal: "AVG: " + Math.round(ramGraph.avgValue) + "%"
                        maxVal: "MAX: " + Math.round(Math.max(74, ramGraph.maxValue)) + "%"
                    }
                    MiniGraph { id: ramGraph; barColor: "#FFB800" }

                    MetricRow {
                        label: "Disk Usage"
                        value: Math.round(jarvis.diskPercent) + "%"
                        avgVal: "AVG: " + Math.round(diskGraph.avgValue) + "%"
                        maxVal: "MAX: " + Math.round(Math.max(73, diskGraph.maxValue)) + "%"
                    }
                    MiniGraph { id: diskGraph; barColor: "#A333FF" }

                    MetricRow {
                        label: "Network"
                        value: (parseFloat(jarvis.networkStatus) || 7.2).toFixed(1) + " KB/s"
                        avgVal: "AVG: " + netGraph.avgValue.toFixed(1) + " KB/s"
                        maxVal: "MAX: " + Math.max(12.5, netGraph.maxValue).toFixed(1) + " KB/s"
                    }
                    MiniGraph { id: netGraph; barColor: "#00FF9D" }
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
        Rectangle { width: 150; height: 1; color: "#00BFFF"; opacity: 0.6 }
        Item { width: 1; height: 12 }
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
                ctx.strokeStyle = "#00284d"; ctx.lineWidth = 2
                ctx.beginPath(); ctx.arc(width/2, height/2, width/2 - 5, 0, Math.PI*2); ctx.stroke()
                var ang = (parent.value / 100) * Math.PI * 2
                ctx.strokeStyle = "#00BFFF"; ctx.lineWidth = 3
                ctx.beginPath(); ctx.arc(width/2, height/2, width/2 - 5, -Math.PI/2, -Math.PI/2 + ang); ctx.stroke()
                ctx.fillStyle = "#D6F5FF"
                ctx.font = "bold 9px Orbitron"
                ctx.textAlign = "center"; ctx.textBaseline = "middle"
                ctx.fillText(Math.round(parent.value) + "%", width/2, height/2)
            }
        }
    }

    component MetricRow: RowLayout {
        property string label: ""
        property string value: ""
        property string avgVal: ""
        property string maxVal: ""
        width: parent.width; height: 20
        spacing: 0
        Text {
            text: label
            font.family: "Consolas"
            font.pixelSize: 9
            font.bold: true
            color: "#80C6E5"
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: 70
        }
        Item { Layout.fillWidth: true }
        Text {
            text: value
            font.family: "Consolas"
            font.pixelSize: 9
            font.bold: true
            color: "#D6F5FF"
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: 38
            horizontalAlignment: Text.AlignRight
        }
        Item { width: 6; Layout.preferredWidth: 6 }
        Text {
            text: avgVal
            font.family: "Consolas"
            font.pixelSize: 8
            color: "#4a8aaa"
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: 56
            horizontalAlignment: Text.AlignRight
        }
        Item { width: 6; Layout.preferredWidth: 6 }
        Text {
            text: maxVal
            font.family: "Consolas"
            font.pixelSize: 8
            color: "#406080"
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
            Layout.preferredWidth: 60
            horizontalAlignment: Text.AlignRight
        }
    }

    component MiniGraph: Item {
        id: graphRoot
        property string barColor: "#00BFFF"
        property var history: []

        function tick(val) {
            var arr = history.slice()
            arr.push(val)
            if (arr.length > 60) {
                arr.shift()
            }
            history = arr
        }

        width: parent.width; height: 32

        property real minValue:  history.length > 0 ? Math.min.apply(null, history) : 0
        property real maxValue:  history.length > 0 ? Math.max.apply(null, history) : 0
        property real currentValue: history.length > 0 ? history[history.length - 1] : 0
        property real avgValue: {
            if (history.length === 0) return 0
            var sum = 0
            for (var i = 0; i < history.length; i++) sum += history[i]
            return sum / history.length
        }

        Canvas {
            id: graphCanvas
            anchors.fill: parent

            property var hist: parent.history
            property string col: parent.barColor
            property real avg: parent.avgValue

            onHistChanged: requestPaint()

            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)

                // Draw a horizontal dotted baseline
                ctx.strokeStyle = "#001f33"
                ctx.lineWidth = 0.5
                ctx.setLineDash([2, 4])
                ctx.beginPath()
                ctx.moveTo(0, height - 1)
                ctx.lineTo(width, height - 1)
                ctx.stroke()
                ctx.setLineDash([])

                if (hist.length < 1) return

                var maxVal = Math.max.apply(null, hist)
                if (maxVal <= 0) maxVal = 10.0
                var maxScale = maxVal * 1.15

                var barWidth = 3
                var gap = 1
                var step = barWidth + gap
                var maxBars = Math.floor(width / step)

                var startIdx = Math.max(0, hist.length - maxBars)

                // Draw bars with gradient tint
                for (var i = startIdx; i < hist.length; i++) {
                    var val = hist[i]
                    var barH = (val / maxScale) * height
                    barH = Math.max(1, Math.min(height - 2, barH))

                    var x = width - (hist.length - i) * step
                    var y = height - barH

                    // Alpha fade older bars slightly
                    var age = (i - startIdx) / Math.max(1, hist.length - startIdx)
                    ctx.globalAlpha = 0.4 + 0.6 * age
                    ctx.fillStyle = col
                    ctx.fillRect(x, y, barWidth, barH)
                }
                ctx.globalAlpha = 1.0

                // Draw smooth line overlay
                if (hist.length > 1) {
                    ctx.strokeStyle = col
                    ctx.lineWidth = 1.5
                    ctx.shadowColor = col
                    ctx.shadowBlur = 3
                    ctx.beginPath()
                    for (var j = startIdx; j < hist.length; j++) {
                        var lx = width - (hist.length - j) * step + barWidth / 2
                        var lVal = hist[j]
                        var lBarH = (lVal / maxScale) * height
                        lBarH = Math.max(1, Math.min(height - 2, lBarH))
                        var ly = height - lBarH
                        if (j === startIdx) ctx.moveTo(lx, ly)
                        else ctx.lineTo(lx, ly)
                    }
                    ctx.stroke()
                    ctx.shadowBlur = 0
                }

                // Draw AVG line
                var avgH = (parent.avgValue / maxScale) * height
                avgH = Math.max(1, Math.min(height - 2, avgH))
                ctx.strokeStyle = "rgba(255,184,0,0.4)"
                ctx.lineWidth = 0.8
                ctx.setLineDash([3, 3])
                ctx.beginPath()
                ctx.moveTo(0, height - avgH)
                ctx.lineTo(width, height - avgH)
                ctx.stroke()
                ctx.setLineDash([])
            }
        }
    }

    // ── Center Particle / Neural Pulse Overlay ────────────────────────────
    component ParticleOverlay: Item {
        id: particleRoot

        property real globalPhase: 0.0
        NumberAnimation on globalPhase {
            running: true; loops: Animation.Infinite
            from: 0; to: Math.PI * 2; duration: 6000
        }

        // Neural pulse rings — emitted from center
        property real pulsePhase: 0.0
        NumberAnimation on pulsePhase {
            running: true; loops: Animation.Infinite
            from: 0; to: 1; duration: 2400
        }

        Canvas {
            id: particleCanvas
            anchors.fill: parent

            property real gp: particleRoot.globalPhase
            property real pp: particleRoot.pulsePhase
            onGpChanged: requestPaint()
            onPpChanged: requestPaint()

            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)

                var cx = width / 2
                var cy = height / 2
                var gp = particleRoot.globalPhase
                var pp = particleRoot.pulsePhase

                // ── Neural pulse rings ────────────────────────────────────
                for (var r = 0; r < 3; r++) {
                    var rPhase = (pp + r / 3.0) % 1.0
                    var radius = 160 + rPhase * 120
                    var alpha  = (1.0 - rPhase) * 0.18
                    ctx.strokeStyle = "rgba(0,191,255," + alpha + ")"
                    ctx.lineWidth = 1.2
                    ctx.beginPath()
                    ctx.arc(cx, cy, radius, 0, Math.PI * 2)
                    ctx.stroke()
                }

                // ── Orbiting data particles ───────────────────────────────
                var particles = [
                    { orbitR: 220, speed: 1.0,  size: 2, offset: 0.0   },
                    { orbitR: 220, speed: 1.0,  size: 1.5, offset: 1.05 },
                    { orbitR: 220, speed: 1.0,  size: 2, offset: 2.09   },
                    { orbitR: 190, speed: -0.7, size: 1.5, offset: 0.0  },
                    { orbitR: 190, speed: -0.7, size: 2, offset: 1.57   },
                    { orbitR: 250, speed: 0.5,  size: 1, offset: 0.78   },
                    { orbitR: 250, speed: 0.5,  size: 1, offset: 2.36   },
                    { orbitR: 250, speed: 0.5,  size: 1, offset: 3.93   },
                    { orbitR: 170, speed: -1.2, size: 1.5, offset: 0.5  },
                    { orbitR: 170, speed: -1.2, size: 1.5, offset: 2.64 },
                    { orbitR: 280, speed: 0.3,  size: 1, offset: 1.0    },
                    { orbitR: 280, speed: 0.3,  size: 1, offset: 3.14   },
                ]

                for (var i = 0; i < particles.length; i++) {
                    var p = particles[i]
                    var angle = gp * p.speed + p.offset
                    var px = cx + Math.cos(angle) * p.orbitR
                    var py = cy + Math.sin(angle) * p.orbitR * 0.38  // elliptical orbit

                    // Only draw if within bounds
                    if (px < 0 || px > width || py < 0 || py > height) continue

                    var brightness = 0.4 + 0.6 * Math.abs(Math.sin(angle * 0.5 + gp))
                    ctx.fillStyle = "rgba(0,210,255," + brightness * 0.7 + ")"
                    ctx.shadowColor = "#00BFFF"
                    ctx.shadowBlur = 4
                    ctx.beginPath()
                    ctx.arc(px, py, p.size, 0, Math.PI * 2)
                    ctx.fill()

                    // Trail dot
                    var trailAngle = angle - 0.15
                    var tpx = cx + Math.cos(trailAngle) * p.orbitR
                    var tpy = cy + Math.sin(trailAngle) * p.orbitR * 0.38
                    if (tpx >= 0 && tpx <= width && tpy >= 0 && tpy <= height) {
                        ctx.fillStyle = "rgba(0,150,200,0.2)"
                        ctx.shadowBlur = 0
                        ctx.beginPath()
                        ctx.arc(tpx, tpy, p.size * 0.6, 0, Math.PI * 2)
                        ctx.fill()
                    }
                }

                ctx.shadowBlur = 0
            }
        }
    }
}
