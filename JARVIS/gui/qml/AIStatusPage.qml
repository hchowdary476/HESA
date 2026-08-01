// AIStatusPage.qml — Premium AI Orchestrator Telemetry & Debate Cockpit

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: aiStatusRoot

    property string aiStatusJson: jarvis.hybridAIStatus

    Connections {
        target: jarvis
        function onHybridAIStatusChanged(jsonStr) {
            aiStatusRoot.aiStatusJson = jsonStr
        }
    }

    function getProvField(provName, fieldName) {
        try {
            var data = JSON.parse(aiStatusJson)
            if (data && data.stats && data.stats[provName.toUpperCase()]) {
                return data.stats[provName.toUpperCase()][fieldName] || "Never"
            }
        } catch (e) {}
        return "Never"
    }

    function getProvStatus(provName) {
        try {
            var data = JSON.parse(aiStatusJson)
            if (data) {
                var key = provName.toLowerCase() + "_status"
                return (data[key] || "UNCONFIGURED").toUpperCase()
            }
        } catch (e) {}
        return "UNCONFIGURED"
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: 32
        contentHeight: mainCol.implicitHeight
        clip: true

        ColumnLayout {
            id: mainCol
            width: parent.width
            spacing: 24

            // Page Title
            RowLayout {
                Layout.fillWidth: true
                Column {
                    spacing: 2
                    Text {
                        text: "HYBRID AI ROUTER COCKPIT"
                        font.family: JarvisFont.orbitron
                        font.pixelSize: 22
                        font.bold: true
                        color: "#00BFFF"
                    }
                    Text {
                        text: "MULTI-MODEL ROUTING & COGNITIVE FAILOVER"
                        font.family: JarvisFont.orbitron
                        font.pixelSize: 9
                        font.bold: true
                        color: "#00FF9D"
                    }
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    width: 140; height: 32
                    color: probeHover.containsMouse ? "#0d2238" : "#08101a"
                    border.color: "#00BFFF"
                    border.width: 1
                    radius: 4
                    Text {
                        anchors.centerIn: parent
                        text: "🔄 PROBE NETWORK"
                        font.family: JarvisFont.orbitron
                        font.pixelSize: 9
                        font.bold: true
                        color: "#00BFFF"
                    }
                    MouseArea {
                        id: probeHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: jarvis.probeAIProviders()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true; height: 1
                color: "#004b73"; opacity: 0.6
            }

            // Summary Telemetry Cards
            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                Repeater {
                    model: [
                        { label: "ACTIVE ORCHESTRATOR", value: jarvis.activeAI, color: "#D6F5FF" },
                        { label: "COGNITIVE MODEL", value: jarvis.activeModel, color: "#00FF9D" },
                        { label: "PROBE LATENCY", value: jarvis.latencyMs.toFixed(0) + " ms", color: "#00BFFF" },
                        { label: "CUMULATIVE COST", value: "$" + jarvis.estimatedCost.toFixed(5), color: "#FFB800" },
                        { label: "ACCUMULATED TOKENS", value: jarvis.tokenUsage.toLocaleString(), color: "#80C6E5" }
                    ]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 70
                        color: "#08101a"
                        border.color: "#004b73"
                        radius: 5
                        Column {
                            anchors.centerIn: parent
                            spacing: 4
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.label
                                font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true; color: "#80C6E5"
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.value
                                font.family: JarvisFont.orbitron; font.pixelSize: 13; font.bold: true; color: modelData.color
                            }
                        }
                    }
                }
            }

            Text {
                text: "PROVIDER FAILOVER STATS"
                font.family: JarvisFont.orbitron
                font.pixelSize: 12
                font.bold: true
                color: "#00BFFF"
            }

            // Main Provider Cards Row
            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                // GROQ Card
                ProviderCard {
                    providerName: "GROQ"
                    providerDesc: "Free/Cloud Llama3 Inference"
                    statusText: aiStatusRoot.getProvStatus("groq")
                    latencyText: aiStatusRoot.getProvField("groq", "response_time")
                    lastSuccess: aiStatusRoot.getProvField("groq", "last_success")
                    lastFailure: aiStatusRoot.getProvField("groq", "last_failure")
                }

                // GEMINI Card
                ProviderCard {
                    providerName: "GEMINI"
                    providerDesc: "Google Flash Multi-modal Cloud"
                    statusText: aiStatusRoot.getProvStatus("gemini")
                    latencyText: aiStatusRoot.getProvField("gemini", "response_time")
                    lastSuccess: aiStatusRoot.getProvField("gemini", "last_success")
                    lastFailure: aiStatusRoot.getProvField("gemini", "last_failure")
                }

                // OLLAMA Card
                ProviderCard {
                    providerName: "OLLAMA"
                    providerDesc: "Local Hardware Coprocessor"
                    statusText: aiStatusRoot.getProvStatus("ollama")
                    latencyText: aiStatusRoot.getProvField("ollama", "response_time")
                    lastSuccess: aiStatusRoot.getProvField("ollama", "last_success")
                    lastFailure: aiStatusRoot.getProvField("ollama", "last_failure")
                }
            }

            // AI INTEGRATION VERIFICATION PANEL
            SectionHeader { text: "AI INTEGRATION VERIFICATION PANEL" }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 220
                color: "#08101a"
                border.color: "#004b73"
                radius: 6
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    // Header row
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Text { text: "PROVIDER"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 120 }
                        Text { text: "CONNECTION STATUS"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 150 }
                        Text { text: "RESPONSE TIME"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 120 }
                        Text { text: "API KEY LOADED"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 130 }
                        Text { text: "LAST SUCCESSFUL CALL"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.fillWidth: true }
                    }

                    Rectangle {
                        Layout.fillWidth: true; height: 1; color: "#004b73"; opacity: 0.5
                    }

                    // Providers repeater
                    Repeater {
                        model: JSON.parse(jarvis.aiIntegrationHealth)
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            height: 24
                            spacing: 0

                            Text {
                                text: modelData.provider
                                font.family: "Consolas"; font.pixelSize: 10; font.bold: true
                                color: "#FFFFFF"
                                Layout.preferredWidth: 120
                            }

                            RowLayout {
                                Layout.preferredWidth: 150
                                spacing: 6
                                Rectangle {
                                    width: 6; height: 6; radius: 3
                                    color: modelData.status === "ONLINE" || modelData.status === "READY" ? "#00FF9D" : "#FF3366"
                                }
                                Text {
                                    text: modelData.status
                                    font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true
                                    color: modelData.status === "ONLINE" || modelData.status === "READY" ? "#00FF9D" : "#FF3366"
                                }
                            }

                            Text {
                                text: modelData.latency
                                font.family: "Consolas"; font.pixelSize: 10; font.bold: true
                                color: modelData.status === "ONLINE" || modelData.status === "READY" ? "#00FF9D" : "#80A0C0"
                                Layout.preferredWidth: 120
                            }

                            Text {
                                text: modelData.api_key_loaded
                                font.family: "Consolas"; font.pixelSize: 10; font.bold: true
                                color: modelData.api_key_loaded === "YES" ? "#00FF9D" : (modelData.api_key_loaded === "LOCAL" ? "#00BFFF" : "#FF3366")
                                Layout.preferredWidth: 130
                            }

                            Text {
                                text: modelData.last_success
                                font.family: "Consolas"; font.pixelSize: 9
                                color: "#A0C0E0"
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            // Parallel Debate Launchpad
            SectionHeader { text: "MULTI-AI SYNAPSE DEBATE GENERATOR" }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                color: "#08101a"
                border.color: "#004b73"
                radius: 6

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    Text {
                        text: "Enter a query to trigger parallel inference and score-synthesis across ChatGPT, Gemini, and Claude:"
                        font.family: "Consolas"; font.pixelSize: 10; color: "#80C6E5"
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#050814"
                        border.color: "#004b73"
                        radius: 4

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: 8
                            TextArea {
                                id: debatePromptInput
                                font.family: "Consolas"; font.pixelSize: 11; color: "#FFFFFF"
                                selectByMouse: true
                                wrapMode: TextArea.Wrap
                                placeholderText: "e.g., Contrast symmetric vs asymmetric encryption with reference to execution speeds and safety."
                                placeholderTextColor: "#406080"
                            }
                        }
                    }

                    Rectangle {
                        Layout.alignment: Qt.AlignRight
                        width: 250; height: 35
                        color: debateBtnHover.containsMouse ? "#00BFFF" : "#0c1a30"
                        border.color: "#00BFFF"
                        border.width: 1
                        radius: 4

                        Text {
                            anchors.centerIn: parent
                            text: "💥 INITIATE PARALLEL DEBATE"
                            font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#FFFFFF"
                        }

                        MouseArea {
                            id: debateBtnHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (debatePromptInput.text.trim() !== "") {
                                    jarvis.startAIDebate(debatePromptInput.text)
                                    debatePromptInput.text = ""
                                }
                            }
                        }
                    }
                }
            }

            // Explainable AI Reasoning Panel
            SectionHeader { text: "EXPLAINABLE AI REASONING COCKPIT" }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                color: "#08101a"
                border.color: "#004b73"
                radius: 6

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    property var expData: {
                        try {
                            return JSON.parse(jarvis.aiExplanation)
                        } catch(e) {
                            return {
                                "why": "Idle. Awaiting user command inputs, sir.",
                                "model": "Cognitive Core (Ollama Fallback)",
                                "confidence": 1.0,
                                "alternatives": ["talk"],
                                "reasoning": "Standby routing active."
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "ACTIVE MODEL:"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 150 }
                        Text { text: parent.parent.expData.model || "None"; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#00FF9D"; Layout.fillWidth: true }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "DECISION CONFIDENCE:"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 150 }
                        Text { text: (parent.parent.expData.confidence * 100).toFixed(1) + "%"; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#FFB800"; Layout.fillWidth: true }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "DECISION RATIONALE:"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 150 }
                        Text { text: parent.parent.expData.why || "None"; font.family: "Consolas"; font.pixelSize: 10; color: "#FFFFFF"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "ALTERNATIVE ACTIONS:"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 150 }
                        Text { text: parent.parent.expData.alternatives ? parent.parent.expData.alternatives.join(", ") : "None"; font.family: "Consolas"; font.pixelSize: 10; color: "#A0C0E0"; Layout.fillWidth: true }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "REASONING LOGS:"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 150 }
                        Text { text: parent.parent.expData.reasoning || "None"; font.family: "Consolas"; font.pixelSize: 10; color: "#80A0C0"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    }
                }
            }

            // Multi-Agent System Panel
            SectionHeader { text: "MULTI-AGENT ORCHESTRATOR & AGENT HEALTH" }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 240
                color: "#08101a"
                border.color: "#004b73"
                radius: 6
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Text { text: "AGENT NAME"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 160 }
                        Text { text: "STATUS"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 120 }
                        Text { text: "CPU/RAM"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 120 }
                        Text { text: "SUCCESS RATE"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.preferredWidth: 120 }
                        Text { text: "PENDING TASKS"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5"; Layout.fillWidth: true }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#004b73"; opacity: 0.5 }

                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true
                        ListView {
                            id: agentsListView
                            model: jarvis.agentHealthJson !== "[]" ? JSON.parse(jarvis.agentHealthJson) : []
                            delegate: RowLayout {
                                width: agentsListView.width
                                height: 24
                                spacing: 0
                                Text { text: modelData.name; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#FFFFFF"; Layout.preferredWidth: 160 }
                                
                                RowLayout {
                                    Layout.preferredWidth: 120
                                    spacing: 4
                                    Rectangle { width: 6; height: 6; radius: 3; color: modelData.status === "IDLE" ? "#00FF9D" : (modelData.status === "BUSY" ? "#FFB800" : "#FF3366") }
                                    Text { text: modelData.status; font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true; color: modelData.status === "IDLE" ? "#00FF9D" : (modelData.status === "BUSY" ? "#FFB800" : "#FF3366") }
                                }
                                
                                Text { text: modelData.cpu + "% / " + modelData.ram + " MB"; font.family: "Consolas"; font.pixelSize: 9; color: "#80A0C0"; Layout.preferredWidth: 120 }
                                Text { text: modelData.success_rate + "%"; font.family: "Consolas"; font.pixelSize: 9; color: "#00FF9D"; Layout.preferredWidth: 120 }
                                Text { text: modelData.pending_tasks + " enqueued"; font.family: "Consolas"; font.pixelSize: 9; color: modelData.pending_tasks > 0 ? "#FFB800" : "#80C6E5"; Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }

            // Predictive Intelligence Forecast
            SectionHeader { text: "PREDICTIVE RESOURCE INTEGRITY FORECASTS" }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 160
                color: "#08101a"
                border.color: "#004b73"
                radius: 6

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    property var predictionData: {
                        try {
                            return JSON.parse(jarvis.predictionAlerts)
                        } catch(e) {
                            return {"alerts": [], "accuracy": 92.5}
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "PREDICTION ENGINE ACCURACY:"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#80C6E5" }
                        Text { text: parent.parent.predictionData.accuracy + "% CONFIDENCE"; font.family: "Consolas"; font.pixelSize: 10; font.bold: true; color: "#00FF9D" }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#004b73"; opacity: 0.5 }

                    ScrollView {
                        id: predScroll
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true
                        ListView {
                            id: predListView
                            model: parent.parent.predictionData.alerts || []
                            delegate: RowLayout {
                                width: predListView.width
                                height: 24
                                spacing: 8
                                Text { text: "⚠️ FORECAST:"; font.family: JarvisFont.orbitron; font.pixelSize: 9; font.bold: true; color: "#FFB800"; Layout.preferredWidth: 90 }
                                Text { text: modelData.message; font.family: "Consolas"; font.pixelSize: 10; color: "#FFFFFF"; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: "Est: " + modelData.value + "%"; font.family: "Consolas"; font.pixelSize: 9; font.bold: true; color: "#FF3366"; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                            }
                        }
                        
                        Text {
                            anchors.centerIn: parent
                            visible: (parent.parent.predictionData.alerts || []).length === 0
                            text: "No resource threshold violations enqueued or predicted, sir."
                            font.family: "Consolas"; font.pixelSize: 10; color: "#4a7a9b"
                        }
                    }
                }
            }
        }
    }

    // ── Inline Helper components ──────────────────────────────────────────

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
        Item { width: 1; height: 4 }
    }

    component ProviderCard: Rectangle {
        property string providerName: ""
        property string providerDesc: ""
        property string statusText: ""
        property string latencyText: ""
        property string lastSuccess: ""
        property string lastFailure: ""

        Layout.fillWidth: true
        Layout.preferredHeight: 160
        color: "#050814"
        border.color: "#004b73"
        radius: 6

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Column {
                    Text { text: providerName; font.family: JarvisFont.orbitron; font.pixelSize: 13; font.bold: true; color: "#00BFFF" }
                    Text { text: providerDesc; font.family: "Consolas"; font.pixelSize: 8; color: "#80C6E5" }
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    width: 90; height: 20; radius: 3
                    color: statusText === "ACTIVE" ? "#0c281e" : (statusText === "COOLDOWN" ? "#281f0c" : "#280c10")
                    border.color: statusText === "ACTIVE" ? "#00FF9D" : (statusText === "COOLDOWN" ? "#FFB800" : "#FF3366")
                    Text {
                        anchors.centerIn: parent
                        text: statusText
                        font.family: JarvisFont.orbitron; font.pixelSize: 8; font.bold: true
                        color: statusText === "ACTIVE" ? "#00FF9D" : (statusText === "COOLDOWN" ? "#FFB800" : "#FF3366")
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 0.5; color: "#004b73"; opacity: 0.4 }

            GridLayout {
                columns: 2
                rowSpacing: 4
                columnSpacing: 8
                Layout.fillWidth: true

                Text { text: "LAST RUN LATENCY:"; font.family: JarvisFont.orbitron; font.pixelSize: 7; color: "#80A0C0" }
                Text { text: latencyText; font.family: "Consolas"; font.pixelSize: 8; font.bold: true; color: "#FFFFFF" }

                Text { text: "LAST SUCCESSFUL CALL:"; font.family: JarvisFont.orbitron; font.pixelSize: 7; color: "#80A0C0" }
                Text { text: lastSuccess !== "Never" ? lastSuccess.replace("T", " ").substring(0, 19) : "Never"; font.family: "Consolas"; font.pixelSize: 8; color: "#A0C0E0" }

                Text { text: "LAST DETECTED FAIL:"; font.family: JarvisFont.orbitron; font.pixelSize: 7; color: "#80A0C0" }
                Text { text: lastFailure !== "Never" ? lastFailure.replace("T", " ").substring(0, 19) : "Never"; font.family: "Consolas"; font.pixelSize: 8; color: "#FF8080" }
            }
        }
    }
}
