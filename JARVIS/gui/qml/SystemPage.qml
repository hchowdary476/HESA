// SystemPage.qml — System health and real-time Windows integration page

import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Item {
    id: sysRoot

    property string systemJson: "{}"
    property string windowsInfoJson: jarvis.windowsSystemInfo
    property var processList: []
    property string processSearch: ""
    property string sortColumn: "cpu"    // "cpu" | "ram" | "pid" | "name"
    property bool   sortAsc: false
    property int    selectedPid: -1
    property string selectedName: ""
    property bool   showKillDialog: false
    property bool   showDetailDialog: false
    property var    detailProcess: null

    // ── Filtered + sorted process list ─────────────────────────────────
    property var filteredList: {
        var src = sysRoot.processList
        var q   = sysRoot.processSearch.trim().toLowerCase()

        // Filter by search term
        if (q.length > 0) {
            src = src.filter(function(p) {
                return p.name.toLowerCase().indexOf(q) !== -1 ||
                       String(p.pid).indexOf(q) !== -1
            })
        }

        // Sort
        var col = sysRoot.sortColumn
        var asc = sysRoot.sortAsc
        src = src.slice().sort(function(a, b) {
            var va = a[col]; var vb = b[col]
            if (typeof va === "string") {
                return asc ? va.localeCompare(vb) : vb.localeCompare(va)
            }
            return asc ? va - vb : vb - va
        })
        return src
    }

    function refreshProcessList() {
        try {
            var jsonStr = jarvis.getProcessListJson()
            sysRoot.processList = JSON.parse(jsonStr)
            processListView.model = sysRoot.filteredList
        } catch(e) {
            sysRoot.processList = []
        }
    }

    // Re-run model whenever filter/sort changes
    onFilteredListChanged: {
        processListView.model = sysRoot.filteredList
    }

    Component.onCompleted: {
        refreshProcessList()
    }

    Connections {
        target: jarvis
        function onSystemStatusChanged(json) { sysRoot.systemJson = json }
        function onWindowsSystemInfoChanged(json) { sysRoot.windowsInfoJson = json }
    }

    function getEngineField(engineKey, fieldName) {
        try {
            var data = JSON.parse(systemJson)
            if (data && data[engineKey]) {
                var val = data[engineKey][fieldName]
                return val !== undefined && val !== null ? val : (fieldName === "restart_count" ? 0 : "N/A")
            }
        } catch(e) {}
        return fieldName === "status" ? "OFFLINE" : (fieldName === "restart_count" ? 0 : "N/A")
    }

    function getWindowsField(fieldName) {
        try {
            var data = JSON.parse(windowsInfoJson)
            if (data) { return data[fieldName] || "Loading..." }
        } catch(e) {}
        return "Loading..."
    }

    // ── Column width constants (fixed widths, name fills remaining) ──────
    readonly property int colPid:    100
    readonly property int colCpu:    90
    readonly property int colRam:    90
    readonly property int colStatus: 110
    readonly property int colKill:   100
    readonly property int colSpacing: 6
    readonly property int rowMargin:  8

    // ══════════════════════════════════════════════════════════════════
    // KILL CONFIRMATION DIALOG
    // ══════════════════════════════════════════════════════════════════
    Rectangle {
        id: killDialogOverlay
        anchors.fill: parent
        color: "#88000000"
        z: 100
        visible: sysRoot.showKillDialog

        Rectangle {
            anchors.centerIn: parent
            width: 400; height: 180
            color: "#05101e"
            border.color: "#FF4B4B"
            border.width: 2
            radius: 8

            ColumnLayout {
                anchors.fill: parent; anchors.margins: 24; spacing: 16

                Text {
                    text: "⚠  TERMINATE PROCESS?"
                    font.family: JarvisFont.orbitron; font.pixelSize: 14; font.bold: true
                    color: "#FF4B4B"
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "PID " + sysRoot.selectedPid + " — " + sysRoot.selectedName
                    font.family: "Consolas"; font.pixelSize: 11
                    color: "#FFFFFF"
                    Layout.alignment: Qt.AlignHCenter
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                }

                RowLayout {
                    Layout.fillWidth: true; spacing: 16
                    Item { Layout.fillWidth: true }

                    Rectangle {
                        width: 120; height: 36
                        color: cancelHover.containsMouse ? "#0d2238" : "#0c1a30"
                        border.color: "#00BFFF"; radius: 4
                        Text { anchors.centerIn: parent; text: "CANCEL"; font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true; color: "#00BFFF" }
                        MouseArea {
                            id: cancelHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: sysRoot.showKillDialog = false
                        }
                    }

                    Rectangle {
                        width: 120; height: 36
                        color: confirmKillHover.containsMouse ? "#801B1B" : "#400c0c"
                        border.color: "#FF4B4B"; radius: 4
                        Text { anchors.centerIn: parent; text: "END TASK"; font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true; color: "#FF4B4B" }
                        MouseArea {
                            id: confirmKillHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                jarvis.killProcess(sysRoot.selectedPid)
                                sysRoot.showKillDialog = false
                                Qt.callLater(sysRoot.refreshProcessList)
                            }
                        }
                    }
                    Item { Layout.fillWidth: true }
                }
            }
        }
    }

    // ══════════════════════════════════════════════════════════════════
    // PROCESS DETAIL POPUP
    // ══════════════════════════════════════════════════════════════════
    Rectangle {
        id: detailDialogOverlay
        anchors.fill: parent
        color: "#88000000"
        z: 100
        visible: sysRoot.showDetailDialog && sysRoot.detailProcess !== null

        Rectangle {
            anchors.centerIn: parent
            width: 380; height: 240
            color: "#05101e"
            border.color: "#00BFFF"
            border.width: 2
            radius: 8

            ColumnLayout {
                anchors.fill: parent; anchors.margins: 24; spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "PROCESS DETAILS"
                        font.family: JarvisFont.orbitron; font.pixelSize: 13; font.bold: true; color: "#00BFFF"
                        Layout.fillWidth: true
                    }
                    Rectangle {
                        width: 28; height: 28; color: closeDetailHover.containsMouse ? "#0d2238" : "#0c1a30"
                        border.color: "#004b73"; radius: 4
                        Text { anchors.centerIn: parent; text: "✕"; font.pixelSize: 12; color: "#80C6E5" }
                        MouseArea { id: closeDetailHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: sysRoot.showDetailDialog = false }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#004b73"; opacity: 0.7 }

                Repeater {
                    model: sysRoot.detailProcess ? [
                        { label: "PROCESS NAME", value: sysRoot.detailProcess.name },
                        { label: "PID",          value: String(sysRoot.detailProcess.pid) },
                        { label: "CPU USAGE",    value: sysRoot.detailProcess.cpu + "%" },
                        { label: "RAM USAGE",    value: sysRoot.detailProcess.ram + "%" },
                        { label: "STATUS",       value: sysRoot.detailProcess.status || "RUNNING" }
                    ] : []
                    delegate: RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: modelData.label + ":"
                            font.family: JarvisFont.orbitron; font.pixelSize: 9; color: "#80A0C0"
                            Layout.preferredWidth: 130
                        }
                        Text {
                            text: modelData.value
                            font.family: "Consolas"; font.pixelSize: 11; font.bold: true; color: "#FFFFFF"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }
    }

    // ══════════════════════════════════════════════════════════════════
    // MAIN SCROLLABLE CONTENT
    // ══════════════════════════════════════════════════════════════════
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
            id: sysScrollBar
            policy: ScrollBar.AsNeeded
            contentItem: Rectangle {
                implicitWidth: 6
                implicitHeight: 100
                radius: 3
                color: "#00BFFF"
                opacity: sysScrollBar.active ? 0.8 : 0.4
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
            spacing: 24

            // Header Section
            Column {
                spacing: 2
                Text {
                    text: "SYSTEM HEALTH CENTER"
                    font.family: JarvisFont.orbitron; font.pixelSize: 22; font.bold: true
                    color: "#00BFFF"
                }
                Text {
                    text: "SUPERVISOR CONTROLS & MULTI-PROCESS STATS"
                    font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true
                    color: "#00FF9D"
                }
            }

            Rectangle { width: 300; height: 1; color: "#004b73"; opacity: 0.6 }

            // Dynamic Engines Repeater
            RowLayout {
                spacing: 16
                Layout.fillWidth: true

                Repeater {
                    model: [
                        { name: "VOICE ENGINE",     key: "voice_engine" },
                        { name: "MEMORY ENGINE",    key: "memory_engine" },
                        { name: "AI ROUTER",        key: "ai_agents" },
                        { name: "SECURITY SHIELD",  key: "security_engine" },
                        { name: "AUTOMATION",       key: "automation_engine" },
                        { name: "SAFE MODE",        key: "safe_mode" }
                    ]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 110
                        color: "#08101a"
                        border.color: "#004b73"
                        radius: 4

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 4

                            Text {
                                text: modelData.name
                                font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true
                                color: "#80C6E5"
                                Layout.alignment: Qt.AlignHCenter
                            }

                            Text {
                                text: {
                                    var stat = sysRoot.getEngineField(modelData.key, "status");
                                    return stat.toUpperCase();
                                }
                                font.family: JarvisFont.orbitron; font.pixelSize: 11; font.bold: true
                                color: {
                                    var stat = sysRoot.getEngineField(modelData.key, "status").toLowerCase();
                                    if (stat === "healthy" || stat === "active") return "#00FF9D"
                                    if (stat === "inactive" || stat === "standby") return "#808080"
                                    return "#FF3366"
                                }
                                Layout.alignment: Qt.AlignHCenter
                            }

                            Text {
                                text: "PID: " + (sysRoot.getEngineField(modelData.key, "pid") || "N/A") + " | RESTARTS: " + sysRoot.getEngineField(modelData.key, "restart_count")
                                font.family: "Consolas"; font.pixelSize: 8
                                color: "#80A0C0"
                                Layout.alignment: Qt.AlignHCenter
                            }

                            Text {
                                text: sysRoot.getEngineField(modelData.key, "desc") || "N/A"
                                font.family: "Consolas"; font.pixelSize: 7
                                color: "#507090"
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignHCenter
                            }
                        }
                    }
                }
            }

            // Real Windows OS System Integration Section
            SectionHeader { text: "WINDOWS OPERATING SYSTEM INTEGRATION" }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 190
                color: "#050814"
                border.color: "#00BFFF"
                border.width: 1
                radius: 6
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "HOST OS METRICS & TELEMETRY"
                            font.family: JarvisFont.orbitron; font.pixelSize: 11; font.bold: true; color: "#00BFFF"
                        }
                        Item { Layout.fillWidth: true }
                        Rectangle { width: 10; height: 10; radius: 5; color: "#00FF9D" }
                        Text {
                            text: "INTEGRATION SYSTEM LINK: VERIFIED"
                            font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#00FF9D"
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#004b73"; opacity: 0.5 }

                    GridLayout {
                        columns: 2
                        rowSpacing: 10; columnSpacing: 30
                        Layout.fillWidth: true

                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 6
                            RowLayout {
                                Text { text: "OPERATING SYSTEM:"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0" }
                                Text { text: sysRoot.getWindowsField("os"); font.family: "Consolas"; font.pixelSize: 9; font.bold: true; color: "#FFFFFF" }
                            }
                            RowLayout {
                                Text { text: "ACTIVE HOSTNAME:"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0" }
                                Text { text: sysRoot.getWindowsField("hostname"); font.family: "Consolas"; font.pixelSize: 9; font.bold: true; color: "#FFFFFF" }
                            }
                            RowLayout {
                                Text { text: "NETWORK LINK IP:"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0" }
                                Text { text: sysRoot.getWindowsField("ip"); font.family: "Consolas"; font.pixelSize: 9; font.bold: true; color: "#00FF9D" }
                            }
                            RowLayout {
                                Text { text: "PROCESSOR INFO:"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0" }
                                Text { text: sysRoot.getWindowsField("cpu"); font.family: "Consolas"; font.pixelSize: 8; color: "#FFFFFF"; Layout.fillWidth: true; elide: Text.ElideRight }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 6
                            RowLayout {
                                Text { text: "SYSTEM UPTIME:"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0" }
                                Text { text: sysRoot.getWindowsField("uptime"); font.family: "Consolas"; font.pixelSize: 9; font.bold: true; color: "#00BFFF" }
                            }
                            RowLayout {
                                Text { text: "SYSTEM DISK (C:):"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0" }
                                Text { text: sysRoot.getWindowsField("disk"); font.family: "Consolas"; font.pixelSize: 9; font.bold: true; color: "#FFFFFF" }
                            }
                            RowLayout {
                                Text { text: "PHYSICAL MEMORY RAM:"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0" }
                                Text { text: sysRoot.getWindowsField("ram"); font.family: "Consolas"; font.pixelSize: 9; font.bold: true; color: "#FFFFFF" }
                            }
                            RowLayout {
                                Text { text: "WINDOWS STARTUP RUN:"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0" }
                                Text {
                                    text: jarvis.getStartupStatus() ? "ENABLED (HKCU REGISTERED)" : "DISABLED"
                                    font.family: "Consolas"; font.pixelSize: 9; font.bold: true
                                    color: jarvis.getStartupStatus() ? "#00FF9D" : "#FF3366"
                                }
                            }
                        }
                    }
                }
            }

            // System control inputs panel
            RowLayout {
                spacing: 16
                Layout.fillWidth: true

                // ── Left Column: Controls ────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: false
                    Layout.preferredWidth: 1.5
                    spacing: 12

                    // VOLUME & BRIGHTNESS
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 120
                        color: "#08101a"; border.color: "#004b73"; radius: 4

                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 12; spacing: 8
                            Text { text: "AUDIO & VISUAL HARDWARE CONTROL"; font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true; color: "#00BFFF" }

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "VOLUME:"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0"; width: 80 }
                                Slider {
                                    id: volumeSlider; Layout.fillWidth: true
                                    from: 0; to: 100; value: jarvis.systemVolume; stepSize: 5
                                    onMoved: {
                                        if (value !== jarvis.systemVolume) {
                                            jarvis.setSystemVolume(value)
                                        }
                                    }
                                }
                                Text { text: Math.round(volumeSlider.value) + "%"; font.family: "Consolas"; font.pixelSize: 9; color: "#FFFFFF" }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "BRIGHTNESS:"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0"; width: 80 }
                                Slider {
                                    id: brightnessSlider; Layout.fillWidth: true
                                    from: 0; to: 100; value: jarvis.systemBrightness; stepSize: 5
                                    onMoved: {
                                        if (value !== jarvis.systemBrightness) {
                                            jarvis.setSystemBrightness(value)
                                        }
                                    }
                                }
                                Text { text: Math.round(brightnessSlider.value) + "%"; font.family: "Consolas"; font.pixelSize: 9; color: "#FFFFFF" }
                            }
                        }
                    }

                    // APPLICATION LAUNCHER
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 140
                        color: "#08101a"; border.color: "#004b73"; radius: 4

                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 12; spacing: 8
                            Text { text: "QUICK APPLICATIONS LAUNCHER"; font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true; color: "#00BFFF" }

                            GridLayout {
                                columns: 2; rowSpacing: 6; columnSpacing: 10; Layout.fillWidth: true
                                Repeater {
                                    model: [
                                        { label: "📁 SYSTEM EXPLORER", name: "explorer" },
                                        { label: "📝 NOTEPAD TEXT",    name: "notepad" },
                                        { label: "🎨 MS PAINT DRAW",   name: "paint" },
                                        { label: "🧮 CALCULATOR",      name: "calculator" }
                                    ]
                                    delegate: Rectangle {
                                        Layout.fillWidth: true; height: 32
                                        color: appBtnHover.containsMouse ? "#0d2238" : "#0c1a30"
                                        border.color: "#004b73"; radius: 3
                                        Text { anchors.centerIn: parent; text: modelData.label; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#00FF9D" }
                                        MouseArea { id: appBtnHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: jarvis.launchApp(modelData.name) }
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true; spacing: 10
                                Rectangle {
                                    Layout.fillWidth: true; height: 32
                                    color: capBtnHover.containsMouse ? "#004b73" : "#0c1a30"
                                    border.color: "#00BFFF"; radius: 3
                                    Text { anchors.centerIn: parent; text: "📸 TAKE SCREENSHOT"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#00BFFF" }
                                    MouseArea { id: capBtnHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: jarvis.takeSystemScreenshot() }
                                }
                            }
                        }
                    }

                    // CLIPBOARD & STARTUP
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 150
                        color: "#08101a"; border.color: "#004b73"; radius: 4

                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 12; spacing: 8
                            Text { text: "CLIPBOARD INTEGRATION & STARTUP CONFIG"; font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true; color: "#00BFFF" }

                            RowLayout {
                                Layout.fillWidth: true; spacing: 8
                                Rectangle {
                                    Layout.fillWidth: true; height: 32
                                    color: "#050814"; border.color: "#004b73"; radius: 3
                                    TextInput {
                                        id: clipTextInput
                                        anchors.fill: parent; anchors.margins: 8
                                        font.family: "Consolas"; font.pixelSize: 9
                                        color: "#FFFFFF"; selectByMouse: true
                                        Text { text: "Enter text to copy to clipboard..."; font.family: "Consolas"; font.pixelSize: 9; color: "#406080"; visible: clipTextInput.text === "" }
                                    }
                                }
                                Rectangle {
                                    width: 80; height: 32; color: copyBtnHover.containsMouse ? "#0d2238" : "#0c1a30"; border.color: "#00BFFF"; radius: 3
                                    Text { anchors.centerIn: parent; text: "COPY"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#00BFFF" }
                                    MouseArea { id: copyBtnHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: jarvis.setClipboardText(clipTextInput.text) }
                                }
                                Rectangle {
                                    width: 80; height: 32; color: pasteBtnHover.containsMouse ? "#0d2238" : "#0c1a30"; border.color: "#00BFFF"; radius: 3
                                    Text { anchors.centerIn: parent; text: "PASTE"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#00BFFF" }
                                    MouseArea { id: pasteBtnHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: clipTextInput.text = jarvis.getClipboardText() }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "RUN JARVIS ON WINDOWS BOOT:"; font.family: JarvisFont.orbitron; font.pixelSize: 8; color: "#80A0C0" }
                                Item { Layout.fillWidth: true }
                                Switch {
                                    id: startupSwitch
                                    checked: jarvis.getStartupStatus()
                                    onToggled: jarvis.toggleStartup(checked)
                                }
                            }
                        }
                    }
                }

                // ── Right Column: PROCESS MONITOR & KILL SHELL ───────────────
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1.2
                    Layout.minimumHeight: 520
                    Layout.preferredHeight: 520
                    color: "#06101c"
                    border.color: "#004b73"
                    radius: 4

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        // ── Panel Header ──────────────────────────────────────
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            // Title
                            Text {
                                text: "PROCESS MONITOR & KILL SHELL"
                                font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true; color: "#00BFFF"
                            }

                            // Process count badge
                            Rectangle {
                                width: 40; height: 20; radius: 10
                                color: "#0c2040"; border.color: "#004b73"
                                Text {
                                    anchors.centerIn: parent
                                    text: sysRoot.filteredList.length
                                    font.family: "Consolas"; font.pixelSize: 9; font.bold: true; color: "#00BFFF"
                                }
                            }

                            Item { Layout.fillWidth: true }

                            // Refresh button
                            Rectangle {
                                width: 70; height: 26
                                color: procRefreshHover.containsMouse ? "#0d2238" : "#0c1a30"
                                border.color: "#00FF9D"; radius: 3
                                RowLayout {
                                    anchors.centerIn: parent; spacing: 4
                                    Text { text: "↻"; font.pixelSize: 13; color: "#00FF9D" }
                                    Text { text: "REFRESH"; font.family: JarvisFont.orbitron; font.pixelSize: 7; font.bold: true; color: "#00FF9D" }
                                }
                                MouseArea {
                                    id: procRefreshHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                    onClicked: sysRoot.refreshProcessList()
                                }
                            }
                        }

                        // ── Search bar ────────────────────────────────────────
                        Rectangle {
                            Layout.fillWidth: true; height: 30
                            color: "#050814"; border.color: searchField.activeFocus ? "#00BFFF" : "#003050"; radius: 4
                            border.width: searchField.activeFocus ? 1 : 1

                            RowLayout {
                                anchors.fill: parent; anchors.margins: 6; spacing: 6
                                Text { text: "🔍"; font.pixelSize: 12; color: "#406080" }
                                TextInput {
                                    id: searchField
                                    Layout.fillWidth: true
                                    font.family: "Consolas"; font.pixelSize: 10
                                    color: "#FFFFFF"; selectByMouse: true
                                    onTextChanged: sysRoot.processSearch = text
                                    Text {
                                        text: "Search process name or PID..."
                                        font.family: "Consolas"; font.pixelSize: 10; color: "#304860"
                                        visible: searchField.text === ""
                                    }
                                }
                                // Clear button
                                Rectangle {
                                    width: 20; height: 20; radius: 10
                                    color: clearSearchHover.containsMouse ? "#0d2238" : "transparent"
                                    visible: searchField.text !== ""
                                    Text { anchors.centerIn: parent; text: "✕"; font.pixelSize: 10; color: "#80A0C0" }
                                    MouseArea { id: clearSearchHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { searchField.text = ""; sysRoot.processSearch = "" } }
                                }
                            }
                        }

                        // ── Column Header Row ─────────────────────────────────
                        Rectangle {
                            Layout.fillWidth: true; height: 28
                            color: "#041020"
                            border.color: "#003050"; radius: 3

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: sysRoot.rowMargin
                                anchors.rightMargin: sysRoot.rowMargin
                                spacing: sysRoot.colSpacing

                                // PID header
                                Rectangle {
                                    width: sysRoot.colPid; height: parent.height; color: "transparent"
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 2
                                        Text {
                                            text: "PID" + (sysRoot.sortColumn === "pid" ? (sysRoot.sortAsc ? " ▲" : " ▼") : "")
                                            font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true
                                            color: sysRoot.sortColumn === "pid" ? "#00BFFF" : "#80A0C0"
                                        }
                                    }
                                    MouseArea {
                                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                        onClicked: { if (sysRoot.sortColumn === "pid") sysRoot.sortAsc = !sysRoot.sortAsc; else { sysRoot.sortColumn = "pid"; sysRoot.sortAsc = true } }
                                    }
                                }

                                // Name header (fills)
                                Item {
                                    Layout.fillWidth: true
                                    height: parent.height
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "PROCESS NAME" + (sysRoot.sortColumn === "name" ? (sysRoot.sortAsc ? " ▲" : " ▼") : "")
                                        font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true
                                        color: sysRoot.sortColumn === "name" ? "#00BFFF" : "#80A0C0"
                                    }
                                    MouseArea {
                                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                        onClicked: { if (sysRoot.sortColumn === "name") sysRoot.sortAsc = !sysRoot.sortAsc; else { sysRoot.sortColumn = "name"; sysRoot.sortAsc = true } }
                                    }
                                }

                                // CPU header
                                Rectangle {
                                    width: sysRoot.colCpu; height: parent.height; color: "transparent"
                                    Text {
                                        anchors.centerIn: parent
                                        text: "CPU %" + (sysRoot.sortColumn === "cpu" ? (sysRoot.sortAsc ? " ▲" : " ▼") : "")
                                        font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true
                                        color: sysRoot.sortColumn === "cpu" ? "#00FF9D" : "#80A0C0"
                                    }
                                    MouseArea {
                                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                        onClicked: { if (sysRoot.sortColumn === "cpu") sysRoot.sortAsc = !sysRoot.sortAsc; else { sysRoot.sortColumn = "cpu"; sysRoot.sortAsc = false } }
                                    }
                                }

                                // RAM header
                                Rectangle {
                                    width: sysRoot.colRam; height: parent.height; color: "transparent"
                                    Text {
                                        anchors.centerIn: parent
                                        text: "RAM %" + (sysRoot.sortColumn === "ram" ? (sysRoot.sortAsc ? " ▲" : " ▼") : "")
                                        font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true
                                        color: sysRoot.sortColumn === "ram" ? "#D6F5FF" : "#80A0C0"
                                    }
                                    MouseArea {
                                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                        onClicked: { if (sysRoot.sortColumn === "ram") sysRoot.sortAsc = !sysRoot.sortAsc; else { sysRoot.sortColumn = "ram"; sysRoot.sortAsc = false } }
                                    }
                                }

                                // Status header
                                Rectangle {
                                    width: sysRoot.colStatus; height: parent.height; color: "transparent"
                                    Text {
                                        anchors.centerIn: parent
                                        text: "STATUS"
                                        font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true; color: "#80A0C0"
                                    }
                                }

                                // Action header
                                Rectangle {
                                    width: sysRoot.colKill; height: parent.height; color: "transparent"
                                    Text {
                                        anchors.centerIn: parent
                                        text: "ACTION"
                                        font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true; color: "#80A0C0"
                                    }
                                }
                            }
                        }

                        // ── Process List (scrollable) ──────────────────────
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: "transparent"
                            clip: true

                            ListView {
                                id: processListView
                                anchors.fill: parent
                                clip: true
                                spacing: 2
                                boundsBehavior: Flickable.StopAtBounds

                                ScrollBar.vertical: ScrollBar {
                                    id: procScrollBar
                                    policy: ScrollBar.AsNeeded
                                    width: 8
                                    contentItem: Rectangle {
                                        radius: 4
                                        color: procScrollBar.pressed ? "#00BFFF" : "#004b73"
                                    }
                                    background: Rectangle { color: "#041020"; radius: 4 }
                                }

                                // Empty state
                                Text {
                                    anchors.centerIn: parent
                                    visible: processListView.count === 0
                                    text: sysRoot.processSearch.length > 0
                                          ? "No processes match \"" + sysRoot.processSearch + "\""
                                          : "No processes loaded — click REFRESH"
                                    font.family: "Consolas"; font.pixelSize: 11; color: "#304860"
                                    horizontalAlignment: Text.AlignHCenter
                                }

                                delegate: Rectangle {
                                    id: procRow
                                    width: processListView.width - 10   // leave room for scrollbar
                                    height: 32
                                    radius: 3
                                    // Alternating row colours + highlight rules
                                    color: {
                                        if (rowHoverArea.containsMouse) return "#0e2440"
                                        var cpu = modelData.cpu
                                        if (cpu >= 80) return "#1a0808"          // critical red tint
                                        if (cpu >= 50) return "#1a1008"          // high orange tint
                                        return (index % 2 === 0) ? "#060f1a" : "#08131f"   // alternating
                                    }
                                    border.color: {
                                        if (modelData.cpu >= 80) return "#FF3333"
                                        if (modelData.cpu >= 50) return "#FF8C00"
                                        return "#001e38"
                                    }
                                    border.width: 1

                                    MouseArea {
                                        id: rowHoverArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            sysRoot.detailProcess  = modelData
                                            sysRoot.showDetailDialog = true
                                        }
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: sysRoot.rowMargin
                                        anchors.rightMargin: sysRoot.rowMargin
                                        anchors.topMargin: 2
                                        anchors.bottomMargin: 2
                                        spacing: sysRoot.colSpacing

                                        // PID — fixed 90 px
                                        Text {
                                            Layout.preferredWidth: sysRoot.colPid
                                            text: modelData.pid
                                            font.family: "Consolas"; font.pixelSize: 9
                                            color: "#6AADCF"
                                            elide: Text.ElideRight
                                        }

                                        // Process Name — expands
                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.name
                                            font.family: "Consolas"; font.pixelSize: 9; font.bold: true
                                            color: {
                                                if (modelData.cpu >= 80) return "#FF6060"
                                                if (modelData.cpu >= 50) return "#FFB347"
                                                return "#E8F4FF"
                                            }
                                            elide: Text.ElideRight
                                        }

                                        // CPU % — fixed 80 px
                                        Rectangle {
                                            Layout.preferredWidth: sysRoot.colCpu
                                            height: parent.height
                                            color: "transparent"
                                            RowLayout {
                                                anchors.centerIn: parent
                                                spacing: 4
                                                // Mini bar
                                                Rectangle {
                                                    width: 28; height: 6; radius: 3
                                                    color: "#0c1a2c"
                                                    Rectangle {
                                                        width: Math.min(parent.width, parent.width * modelData.cpu / 100)
                                                        height: parent.height; radius: 3
                                                        color: modelData.cpu >= 80 ? "#FF3333" : modelData.cpu >= 50 ? "#FF8C00" : "#00FF9D"
                                                    }
                                                }
                                                Text {
                                                    text: modelData.cpu + "%"
                                                    font.family: "Consolas"; font.pixelSize: 9; font.bold: true
                                                    color: modelData.cpu >= 80 ? "#FF6060" : modelData.cpu >= 50 ? "#FFB347" : "#00FF9D"
                                                }
                                            }
                                        }

                                        // RAM % — fixed 80 px
                                        Rectangle {
                                            Layout.preferredWidth: sysRoot.colRam
                                            height: parent.height
                                            color: "transparent"
                                            RowLayout {
                                                anchors.centerIn: parent
                                                spacing: 4
                                                Rectangle {
                                                    width: 28; height: 6; radius: 3
                                                    color: "#0c1a2c"
                                                    Rectangle {
                                                        width: Math.min(parent.width, parent.width * modelData.ram / 100)
                                                        height: parent.height; radius: 3
                                                        color: modelData.ram >= 80 ? "#FF3333" : "#4FC3F7"
                                                    }
                                                }
                                                Text {
                                                    text: modelData.ram + "%"
                                                    font.family: "Consolas"; font.pixelSize: 9
                                                    color: modelData.ram >= 80 ? "#FF6060" : "#D6F5FF"
                                                }
                                            }
                                        }

                                        // Status — fixed 100 px
                                        Rectangle {
                                            Layout.preferredWidth: sysRoot.colStatus
                                            height: 20; radius: 3
                                            color: {
                                                var s = (modelData.status || "RUNNING").toUpperCase()
                                                if (s === "RUNNING")  return "#0a2a15"
                                                if (s === "SLEEPING") return "#0a1a2a"
                                                if (s === "STOPPED" || s === "ZOMBIE" || s === "DEAD") return "#2a0a0a"
                                                return "#0f1a2a"
                                            }
                                            border.color: {
                                                var s = (modelData.status || "RUNNING").toUpperCase()
                                                if (s === "RUNNING")  return "#00AA44"
                                                if (s === "SLEEPING") return "#0066AA"
                                                if (s === "STOPPED" || s === "ZOMBIE" || s === "DEAD") return "#CC2200"
                                                return "#004b73"
                                            }
                                            border.width: 1
                                            Text {
                                                anchors.centerIn: parent
                                                text: (modelData.status || "RUNNING")
                                                font.family: "Consolas"; font.pixelSize: 8; font.bold: true
                                                color: {
                                                    var s = (modelData.status || "RUNNING").toUpperCase()
                                                    if (s === "RUNNING")  return "#00FF88"
                                                    if (s === "SLEEPING") return "#4FC3F7"
                                                    if (s === "STOPPED" || s === "ZOMBIE" || s === "DEAD") return "#FF6060"
                                                    return "#80C6E5"
                                                }
                                            }
                                        }

                                        // KILL button — fixed 90 px
                                        Rectangle {
                                            Layout.preferredWidth: sysRoot.colKill
                                            height: 24; radius: 3
                                            color: killBtnHover.containsMouse ? "#801B1B" : "#2a0808"
                                            border.color: "#FF4B4B"; border.width: 1
                                            Text {
                                                anchors.centerIn: parent
                                                text: "END TASK"
                                                font.family: JarvisFont.orbitron; font.pixelSize: 7; font.bold: true; color: "#FF4B4B"
                                            }
                                            MouseArea {
                                                id: killBtnHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    sysRoot.selectedPid  = modelData.pid
                                                    sysRoot.selectedName = modelData.name
                                                    sysRoot.showKillDialog = true
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // ── Sort hint footer ──────────────────────────────────
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Sort: " + sysRoot.sortColumn.toUpperCase() + " (" + (sysRoot.sortAsc ? "ASC" : "DESC") + ")  |  " + sysRoot.filteredList.length + " processes"
                                font.family: "Consolas"; font.pixelSize: 8; color: "#304860"
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: "Click row for details  •  Click header to sort"
                                font.family: "Consolas"; font.pixelSize: 8; color: "#203040"
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
        Rectangle { width: 220; height: 1; color: "#00BFFF"; opacity: 0.6 }
        Item { width: 1; height: 4 }
    }
}
