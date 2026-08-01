// HudEngine.qml — Iron-Man annotation HUD overlay

import QtQuick 2.15

Item {
    id: hudRoot
    anchors.fill: parent

    property string state: "STANDBY"

    Connections {
        target: jarvis
        function onStateChanged(s) { hudRoot.state = s }
    }

    // State-based accent color
    property string accentColor: {
        if (state === "LISTENING")   return "#4CEBFF"
        if (state === "PROCESSING")  return "#89F2FF"
        if (state === "SPEAKING")    return "#4CEBFF"
        if (state === "EXECUTING")   return "#00FFC6"
        if (state === "ERROR")       return "#FF4D6D"
        if (state === "OFFLINE")     return "#FFC857"
        return "#00D7FF"
    }

    Canvas {
        id: hudCanvas
        anchors.fill: parent

        property string accent: hudRoot.accentColor
        onAccentChanged: requestPaint()
        Component.onCompleted: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)

            var cx = width / 2, cy = height / 2
            var col = hudRoot.accentColor

            ctx.strokeStyle = col
            ctx.fillStyle   = col
            ctx.font        = "bold 8px Orbitron"

            // ── Left annotation lines ────────────────────────────────────
            var lines = [
                { sx: cx - 180, sy: cy - 100, ex: cx - 250, ey: cy - 150, label: "NEURAL NETWORK" },
                { sx: cx - 200, sy: cy,       ex: cx - 250, ey: cy,       label: "CORE TEMP 48°C" },
                { sx: cx - 180, sy: cy + 100, ex: cx - 250, ey: cy + 150, label: "EFFICIENCY 96%" },
            ]
            for (var i = 0; i < lines.length; i++) {
                var l = lines[i]
                ctx.beginPath()
                ctx.moveTo(l.sx, l.sy)
                ctx.lineTo(l.ex, l.ey)
                ctx.stroke()
                ctx.textAlign = "right"
                ctx.fillText(l.label, l.ex - 6, l.ey + 4)
                // dot
                ctx.beginPath()
                ctx.arc(l.sx, l.sy, 3, 0, Math.PI * 2)
                ctx.fill()
            }

            // ── Right annotation lines ───────────────────────────────────
            var rlines = [
                { sx: cx + 180, sy: cy - 100, ex: cx + 250, ey: cy - 150, label: "THOUGHT PROCESS" },
                { sx: cx + 200, sy: cy,       ex: cx + 250, ey: cy,       label: "LEARNING MODEL" },
                { sx: cx + 180, sy: cy + 100, ex: cx + 250, ey: cy + 150, label: "RESPONSE TIME 0.02s" },
            ]
            for (var j = 0; j < rlines.length; j++) {
                var r = rlines[j]
                ctx.beginPath()
                ctx.moveTo(r.sx, r.sy)
                ctx.lineTo(r.ex, r.ey)
                ctx.stroke()
                ctx.textAlign = "left"
                ctx.fillText(r.label, r.ex + 6, r.ey + 4)
                ctx.beginPath()
                ctx.arc(r.sx, r.sy, 3, 0, Math.PI * 2)
                ctx.fill()
            }

            // ── Top identifier ───────────────────────────────────────────
            ctx.textAlign = "center"
            ctx.font = "bold 10px Orbitron"
            ctx.fillText("06_JARVIS CONSCIOUSNESS ACTIVATED", cx, cy - 220)

            // ── Outer circular HUD ring (static) ────────────────────────
            ctx.strokeStyle = col
            ctx.lineWidth = 0.8
            ctx.globalAlpha = 0.3
            ctx.beginPath()
            ctx.arc(cx, cy, 210, 0, Math.PI * 2)
            ctx.stroke()
            ctx.globalAlpha = 1.0
        }
    }

    // State label at bottom of face
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height / 2 + 220
        text: {
            if (hudRoot.state === "STANDBY")    return "JARVIS ONLINE"
            if (hudRoot.state === "LISTENING")  return "LISTENING..."
            if (hudRoot.state === "PROCESSING") return "PROCESSING REQUEST"
            if (hudRoot.state === "SPEAKING")   return "RESPONDING..."
            if (hudRoot.state === "EXECUTING")  return "EXECUTING COMMAND"
            if (hudRoot.state === "ERROR")      return "COMMAND FAILED"
            return hudRoot.state
        }
        color: hudRoot.accentColor
        font.family: JarvisFont.orbitron
        font.pixelSize: 11
        font.bold: true

        // Glow pulse
        NumberAnimation on opacity {
            running: hudRoot.state === "LISTENING" || hudRoot.state === "SPEAKING"
            loops: Animation.Infinite
            from: 1.0; to: 0.4; duration: 700
            easing.type: Easing.InOutSine
        }
    }
}
