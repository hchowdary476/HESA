// VoiceVisualizationEngine.qml — Animated waveform display

import QtQuick 2.15

Item {
    id: waveRoot
    width: parent ? parent.width : 200
    height: 40

    property string state: "STANDBY"
    property real   activity: 0.35

    Connections {
        target: jarvis
        function onStateChanged(s) {
            waveRoot.state = s
            if      (s === "LISTENING")  waveRoot.activity = 1.0
            else if (s === "SPEAKING")   waveRoot.activity = 0.95
            else if (s === "PROCESSING") waveRoot.activity = 0.7
            else                         waveRoot.activity = 0.35
        }
    }

    property real phase: 0.0
    NumberAnimation on phase {
        running: true; loops: Animation.Infinite
        from: 0; to: Math.PI * 2; duration: 1200
    }

    Canvas {
        id: waveCanvas
        anchors.fill: parent

        property real p: waveRoot.phase
        property real a: waveRoot.activity
        onPChanged: requestPaint()
        onAChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            var mid = height / 2
            var active = waveRoot.state === "LISTENING" || waveRoot.state === "SPEAKING"
            var barW = 3, gap = 2, barCount = Math.floor(width / (barW + gap))

            for (var i = 0; i < barCount; i++) {
                var xp = i * (barW + gap)
                var h = mid * waveRoot.activity * (
                    0.3 + 0.7 * Math.abs(
                        Math.sin(waveRoot.phase + i * 0.4) *
                        Math.cos(waveRoot.phase * 0.7 + i * 0.3)
                    )
                )

                var alpha = active ? 0.9 : 0.4
                ctx.fillStyle = active ? "rgba(0,255,255," + alpha + ")" : "rgba(0,75,115," + alpha + ")"
                ctx.fillRect(xp, mid - h, barW, h * 2)
            }
        }
    }
}
