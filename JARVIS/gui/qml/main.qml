// main.qml — JARVIS Root Application Window
// GPU-rendered Iron-Man holographic interface via QML + QtQuick

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: root
    title: "JARVIS CYBER INTERFACE"
    width: 1600
    height: 900
    minimumWidth: 1366
    minimumHeight: 768
    visible: true
    color: "#050814"

    // Remove native title bar — we draw our own
    flags: Qt.Window | Qt.FramelessWindowHint

    // ── Window drag support ──────────────────────────────────────────────
    property int dragX: 0
    property int dragY: 0
    property bool dragging: false

    // ── Current page tracker ─────────────────────────────────────────────
    property string activePage: "dashboard"

    onActivePageChanged: {
        var page = activePage
        if      (page === "dashboard")    mainStack.replace(dashComp,     StackView.Immediate)
        else if (page === "system")       mainStack.replace(sysComp,      StackView.Immediate)
        else if (page === "modules")      mainStack.replace(modComp,      StackView.Immediate)
        else if (page === "cybersecurity") mainStack.replace(cyberComp,   StackView.Immediate)
        else if (page === "diagnostics")  mainStack.replace(diagComp,     StackView.Immediate)
        else if (page === "settings")     mainStack.replace(settComp,     StackView.Immediate)
        else if (page === "help")         mainStack.replace(helpComp,     StackView.Immediate)
        else if (page === "aistatus")     mainStack.replace(aiStatusComp, StackView.Immediate)
        else if (page === "ai_ml")        mainStack.replace(aimlComp,     StackView.Immediate)
    }

    // ── Connected state from Python bridge ──────────────────────────────
    property string jarvisState: "BOOTING"
    property bool showDebateWindow: false
    property var parsedHybridStatus: ({})

    Component.onCompleted: {
        try {
            root.parsedHybridStatus = JSON.parse(jarvis.hybridAIStatus)
        } catch(e) {}
    }

    // ── Listen to bridge signals ─────────────────────────────────────────
    Connections {
        target: jarvis
        function onStateChanged(state) {
            root.jarvisState = state
        }
        function onDebateDataChanged(dataJson) {
            if (dataJson && dataJson !== "{}") {
                root.showDebateWindow = true
            }
        }
        function onHybridAIStatusChanged(json) {
            try {
                root.parsedHybridStatus = JSON.parse(json)
            } catch(e) {
                root.parsedHybridStatus = {}
            }
        }
        function onNavigateRequested(page) {
            root.activePage = page
        }
    }

    // ── Background grid / scanline effect ───────────────────────────────
    Canvas {
        id: bgGrid
        anchors.fill: parent
        opacity: 0.04
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.strokeStyle = "#00BFFF"
            ctx.lineWidth = 0.5
            var step = 40
            for (var x = 0; x < width; x += step) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke()
            }
            for (var y = 0; y < height; y += step) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
            }
        }
    }

    // ── Corner HUD brackets ──────────────────────────────────────────────
    Canvas {
        id: hudCorners
        anchors.fill: parent
        opacity: 0.6
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.strokeStyle = "#00BFFF"
            ctx.lineWidth = 2
            var s = 30
            // Top-left
            ctx.beginPath(); ctx.moveTo(0, s); ctx.lineTo(0, 0); ctx.lineTo(s, 0); ctx.stroke()
            // Top-right
            ctx.beginPath(); ctx.moveTo(width - s, 0); ctx.lineTo(width, 0); ctx.lineTo(width, s); ctx.stroke()
            // Bottom-left
            ctx.beginPath(); ctx.moveTo(0, height - s); ctx.lineTo(0, height); ctx.lineTo(s, height); ctx.stroke()
            // Bottom-right
            ctx.beginPath(); ctx.moveTo(width - s, height); ctx.lineTo(width, height); ctx.lineTo(width, height - s); ctx.stroke()
        }
    }

    // ── Main vertical layout ─────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Custom title bar
        TitleBar {
            id: titleBar
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            onMinimizeRequested: root.showMinimized()
            onMaximizeRequested: root.visibility === Window.Maximized
                                    ? root.showNormal() : root.showMaximized()
            onCloseRequested: { root.hide(); /* minimize to tray */ }
            onDragStarted: function(mx, my) { root.dragX = mx; root.dragY = my; root.dragging = true }
            onDragMoved: function(gx, gy) {
                if (root.dragging) {
                    root.x = gx - root.dragX
                    root.y = gy - root.dragY
                }
            }
            onDragEnded: root.dragging = false
        }

        // Content area — StackView navigation.
        // Pages are kept as Components and pushed/replaced as needed.
        // IMPORTANT: Do NOT set anchors.fill on StackView children —
        //            StackView manages their geometry internally.
        //            Setting anchors.fill conflicts and causes console warnings.
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            StackView {
                id: mainStack
                anchors.fill: parent
                initialItem: dashComp

                // ── Page Components ──────────────────────────────────────────
                // Each page is a Component; StackView creates/sizes instances.
                // No anchors.fill or explicit sizing needed here.
                Component { id: dashComp;     DashboardPage   {} }
                Component { id: sysComp;      SystemPage      {} }
                Component { id: modComp;      ModulesPage     {} }
                Component { id: cyberComp;    CyberSecurityPage { objectName: "cyberSecurityPage" } }
                Component { id: diagComp;     DiagnosticsPage {} }
                Component { id: settComp;     SettingsPage    {} }
                Component { id: helpComp;     HelpPage        {} }
                Component { id: aiStatusComp; AIStatusPage    {} }
                Component { id: aimlComp;     AIMLPage        {} }
            }
        }

        // Bottom navigation dock
        BottomDock {
            id: bottomDock
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            activePage: root.activePage
            onPageSelected: function(page) { root.activePage = page }
        }
    }

    // ── Keyboard shortcut: ESC → dashboard ───────────────────────────────
    Shortcut {
        sequence: "Escape"
        onActivated: root.activePage = "dashboard"
    }


    // Multi-AI Debate Comparison Overlay Window
    Rectangle {
        id: debateComparisonWindow
        anchors.centerIn: parent
        width: 1100
        height: 600
        color: "#050814"
        border.color: "#00BFFF"
        border.width: 2
        radius: 8
        visible: root.showDebateWindow
        z: 10000

        // Header
        RowLayout {
            id: debateHeader
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 12

            Text {
                text: "MULTI-AI DEBATE & SYNTHESIS CONTROL"
                font.family: JarvisFont.orbitron
                font.pixelSize: 16
                font.bold: true
                color: "#00BFFF"
            }

            Item { Layout.fillWidth: true }

            // Use Rectangle+MouseArea instead of native Button to avoid
            // Qt style customization warnings while keeping the same look
            Rectangle {
                width: 60; height: 28
                color: closeHover.containsMouse ? "#CC1B1B" : "#FF4B4B"
                radius: 4
                Text {
                    anchors.centerIn: parent
                    text: "CLOSE"
                    font.family: JarvisFont.orbitron
                    font.pixelSize: 10
                    color: "white"
                }
                MouseArea {
                    id: closeHover
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.showDebateWindow = false
                    cursorShape: Qt.PointingHandCursor
                }
            }
        }

        // Side-by-side responses and synthesis
        RowLayout {
            anchors { left: parent.left; right: parent.right; top: debateHeader.bottom; bottom: parent.bottom; margins: 16 }
            spacing: 12

            // Provider 1: ChatGPT
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#08101a"
                border.color: "#004b73"
                border.width: 1
                radius: 4
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    Text { text: "CHATGPT (OPENAI)"; font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true; color: "#00FF9D" }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        TextArea {
                            text: {
                                try {
                                    var data = JSON.parse(jarvis.debateData);
                                    return data.chatgpt || "Awaiting debate analysis..."
                                } catch (e) {
                                    return "No data"
                                }
                            }
                            readOnly: true
                            color: "#E0E0E0"
                            font.family: "Consolas"
                            font.pixelSize: 9
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }

            // Provider 2: Gemini
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#08101a"
                border.color: "#004b73"
                border.width: 1
                radius: 4
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    Text { text: "GEMINI (GOOGLE)"; font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true; color: "#00FF9D" }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        TextArea {
                            text: {
                                try {
                                    var data = JSON.parse(jarvis.debateData);
                                    return data.gemini || "Awaiting debate analysis..."
                                } catch (e) {
                                    return "No data"
                                }
                            }
                            readOnly: true
                            color: "#E0E0E0"
                            font.family: "Consolas"
                            font.pixelSize: 9
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }

            // Provider 3: Claude
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#08101a"
                border.color: "#004b73"
                border.width: 1
                radius: 4
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    Text { text: "CLAUDE (ANTHROPIC)"; font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true; color: "#00FF9D" }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        TextArea {
                            text: {
                                try {
                                    var data = JSON.parse(jarvis.debateData);
                                    return data.claude || "Awaiting debate analysis..."
                                } catch (e) {
                                    return "No data"
                                }
                            }
                            readOnly: true
                            color: "#E0E0E0"
                            font.family: "Consolas"
                            font.pixelSize: 9
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }

            // Unified Synthesized Response
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#0d2238"
                border.color: "#00BFFF"
                border.width: 1.5
                radius: 4
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    Text { text: "UNIFIED SYNTHESIS DECISION"; font.family: JarvisFont.orbitron; font.pixelSize: 10; font.bold: true; color: "#00BFFF" }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        TextArea {
                            text: {
                                try {
                                    var data = JSON.parse(jarvis.debateData);
                                    return data.unified || "Awaiting debate analysis..."
                                } catch (e) {
                                    return "No data"
                                }
                            }
                            readOnly: true
                            color: "#FFFFFF"
                            font.family: "Consolas"
                            font.pixelSize: 9
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }
        }
    }
}
