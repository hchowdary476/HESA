// MapEngine.qml — Global tactical map display
// OPTIMIZED: Static world map is loaded as a GPU-accelerated Image component.
// Dynamic layers (pulsing hubs, connections, and routing particles) are animated on Canvas.

import QtQuick 2.15

Item {
    id: mapRoot
    width: parent ? parent.width : 300
    height: 150

    property string jarvisState: "STANDBY"
    property real   phase: 0.0
    property int    activeNodes: 8

    Connections {
        target: jarvis
        function onStateChanged(s) { mapRoot.jarvisState = s }
    }

    // ── Phase animation — drives ONLY the dynamic canvas ─────────────────
    NumberAnimation on phase {
        id: phaseAnim
        running: mapRoot.visible
        loops: Animation.Infinite
        from: 0; to: Math.PI * 2; duration: 4000
        easing.type: Easing.Linear
    }

    // Hot spots (active connection nodes) — lat/lon pairs + status types
    property var hotSpots: [
        { x: 0.14, y: 0.30, type: "blue" },  // USA
        { x: 0.26, y: 0.52, type: "red"  },  // Brazil (Threat)
        { x: 0.48, y: 0.25, type: "blue" },  // Europe
        { x: 0.50, y: 0.45, type: "red"  },  // Africa (Threat)
        { x: 0.62, y: 0.43, type: "blue" },  // India
        { x: 0.70, y: 0.28, type: "red"  },  // China (Threat)
        { x: 0.78, y: 0.56, type: "blue" },  // Australia
        { x: 0.83, y: 0.26, type: "blue" }   // Japan
    ]

    // Full mesh connections between hotspot index pairs
    property var connections: [
        [0, 2], [0, 4], [0, 1], [0, 5],
        [2, 4], [2, 3], [2, 5], [2, 7],
        [4, 5], [4, 3], [4, 6],
        [5, 6], [5, 7],
        [6, 7], [1, 3], [3, 4]
    ]

    // ── LAYER 1: STATIC WORLD MAP (GPU Accelerated) ─────────────────────
    Image {
        id: staticWorldMap
        source: (typeof assetsPath !== "undefined" && assetsPath !== "") 
                ? "file:///" + assetsPath + "/world_map_hud.png"
                : "../../assets/world_map_hud.png"
        anchors.fill: parent
        fillMode: Image.Stretch
        opacity: 0.55
        visible: status === Image.Ready
    }

    // ── LAYER 2: DYNAMIC OVERLAY (Repaints every frame via phase change) ─
    Canvas {
        id: dynamicMapCanvas
        anchors.fill: parent
        z: 1

        property real p: mapRoot.phase
        onPChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)

            var hot  = mapRoot.hotSpots
            var conn = mapRoot.connections
            var p    = mapRoot.phase

            // 1. Draw connections (curved arcs)
            for (var c = 0; c < conn.length; c++) {
                var ai = conn[c][0], bi = conn[c][1]
                var ax = hot[ai].x * width,  ay = hot[ai].y * height
                var bx = hot[bi].x * width,  by = hot[bi].y * height

                // Control point for curve (arch upwards)
                var midX = (ax + bx) / 2
                var midY = (ay + by) / 2 - 20

                // Primary glowing link line
                ctx.beginPath()
                ctx.moveTo(ax, ay)
                ctx.quadraticCurveTo(midX, midY, bx, by)
                ctx.strokeStyle = "rgba(0, 190, 255, 0.18)"
                ctx.lineWidth = 0.8
                ctx.stroke()

                // Pulsing faint wider glow line
                ctx.beginPath()
                ctx.moveTo(ax, ay)
                ctx.quadraticCurveTo(midX, midY, bx, by)
                ctx.strokeStyle = "rgba(0, 220, 255, " + (0.05 + 0.05 * Math.sin(p + c)) + ")"
                ctx.lineWidth = 1.6
                ctx.stroke()
            }

            // 2. Draw routing particles and airplanes along connections
            for (var d = 0; d < conn.length; d++) {
                var si = conn[d][0], ei = conn[d][1]
                var sx = hot[si].x * width, sy = hot[si].y * height
                var ex = hot[ei].x * width, ey = hot[ei].y * height

                var midX = (sx + ex) / 2
                var midY = (sy + ey) / 2 - 20

                var tRaw = (p / (Math.PI * 2) + d * 0.15) % 1.0
                var t = (d % 2 === 0) ? tRaw : (1.0 - tRaw)

                // Quadratic Bezier interpolation formula
                var dotX = (1-t)*(1-t)*sx + 2*(1-t)*t*midX + t*t*ex
                var dotY = (1-t)*(1-t)*sy + 2*(1-t)*t*midY + t*t*ey

                if (d % 3 === 0) {
                    // Draw flying airplane
                    ctx.save()
                    ctx.translate(dotX, dotY)
                    // Calculate tangent angle for rotation
                    var tx = 2*(1-t)*(midX - sx) + 2*t*(ex - midX)
                    var ty = 2*(1-t)*(midY - sy) + 2*t*(ey - midY)
                    ctx.rotate(Math.atan2(ty, tx))

                    ctx.fillStyle = "#ffffff"
                    ctx.beginPath()
                    ctx.moveTo(4, 0)
                    ctx.lineTo(-4, -3)
                    ctx.lineTo(-2, 0)
                    ctx.lineTo(-4, 3)
                    ctx.closePath()
                    ctx.fill()
                    ctx.restore()
                } else {
                    // Faint outer glow shell
                    ctx.fillStyle = "rgba(0, 255, 210, 0.35)"
                    ctx.beginPath()
                    ctx.arc(dotX, dotY, 3.2, 0, Math.PI * 2)
                    ctx.fill()

                    // Bright core
                    ctx.fillStyle = "rgba(255, 255, 255, 0.95)"
                    ctx.beginPath()
                    ctx.arc(dotX, dotY, 1.4, 0, Math.PI * 2)
                    ctx.fill()
                }
            }

            // 3. Draw active hubs (pulsing secure vs threat nodes)
            for (var k = 0; k < hot.length; k++) {
                var hx = hot[k].x * width, hy = hot[k].y * height
                var pulse = 0.5 + 0.5 * Math.sin(p * 1.5 + k * 1.2)
                var isRed = hot[k].type === "red"

                // Soft radial glow behind the node
                var radialGrad = ctx.createRadialGradient(hx, hy, 1, hx, hy, 8 + pulse * 6)
                if (isRed) {
                    radialGrad.addColorStop(0.0, "rgba(255, 50, 100, 0.45)")
                    radialGrad.addColorStop(0.3, "rgba(255, 50, 100, 0.20)")
                    radialGrad.addColorStop(1.0, "rgba(0, 0, 0, 0)")
                } else {
                    radialGrad.addColorStop(0.0, "rgba(0, 245, 255, 0.35)")
                    radialGrad.addColorStop(0.3, "rgba(0, 210, 255, 0.15)")
                    radialGrad.addColorStop(1.0, "rgba(0, 0, 0, 0)")
                }
                ctx.fillStyle = radialGrad
                ctx.beginPath()
                ctx.arc(hx, hy, 8 + pulse * 6, 0, Math.PI * 2)
                ctx.fill()

                // Core static dot
                ctx.fillStyle = isRed ? "#FF3366" : "#00D7FF"
                ctx.beginPath()
                ctx.arc(hx, hy, 2.2, 0, Math.PI * 2)
                ctx.fill()

                // Expanding radar pulse ring
                ctx.strokeStyle = isRed ? "rgba(255, 50, 100, " + (1.0 - pulse) * 0.7 + ")"
                                        : "rgba(0, 245, 255, " + (1.0 - pulse) * 0.7 + ")"
                ctx.lineWidth = 1.0
                ctx.beginPath()
                ctx.arc(hx, hy, 3.5 + pulse * 9, 0, Math.PI * 2)
                ctx.stroke()
            }
        }
    }

    // ── LAYER 3: MAP LEGEND (Bottom Left Overlay) ────────────────────────
    Column {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 6
        spacing: 3
        z: 2

        Row {
            spacing: 5
            Rectangle { width: 4; height: 4; radius: 2; color: "#00BFFF"; anchors.verticalCenter: parent.verticalCenter }
            Text { text: "ACTIVE CONNECTION"; font.family: "Consolas"; font.pixelSize: 7; font.bold: true; color: "#80C6E5" }
        }
        Row {
            spacing: 5
            Text { text: "✈"; font.pixelSize: 8; color: "#ffffff"; anchors.verticalCenter: parent.verticalCenter }
            Text { text: "FLIGHT PATH"; font.family: "Consolas"; font.pixelSize: 7; font.bold: true; color: "#80C6E5" }
        }
        Row {
            spacing: 5
            Rectangle { width: 4; height: 4; radius: 2; color: "#FF3366"; anchors.verticalCenter: parent.verticalCenter }
            Text { text: "THREAT/HACKER"; font.family: "Consolas"; font.pixelSize: 7; font.bold: true; color: "#80C6E5" }
        }
    }
}

