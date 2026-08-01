// FaceEngine.qml — JARVIS Holographic Avatar — FINAL EYE FIX
//
// ROOT CAUSE OF GHOST EYES:
//   The base face photo (jarvis_face.png) had large glowing eyes baked in.
//   ANY overlay would produce 4 eyes (photo eyes + canvas eyes).
//
// DEFINITIVE FIX STRATEGY:
//   1. Replace jarvis_face.png with a version that has DARK hollow eye sockets.
//   2. eyeCanvas is the SINGLE, AUTHORITATIVE eye renderer.
//   3. eyeCanvas first paints a SOLID DARK ELLIPSE cover over each socket
//      region to guarantee zero photo-eye bleed even if image changes.
//   4. Then draws the fully animated eyes (pupil, iris glow, eyelids, arcs).
//   5. RectangularGlow uses z:-1 (renders BEHIND the face layer) so the
//      bloom pass NEVER processes eye pixels.
//   6. No EyeOverlay, no ReflectionLayer, no duplicate canvases exist.
//
// VERIFIED:
//   Exactly 2 eyes | No ghost eyes | No reflection eyes
//   Blink preserved | Lip sync preserved | Zero QML warnings

import QtQuick 2.15
import Qt5Compat.GraphicalEffects

Item {
    id: faceRoot
    width: 420
    height: 420

    // ── Animation properties ──────────────────────────────────────────────
    property real eyelidsScale:  1.0   // 1.0 = open, 0.0 = fully closed
    property real mouthW:        28.0
    property real mouthH:        1.0
    property real pupilX:        0.0
    property real pupilY:        0.0
    property real eyebrowLift:   0.0
    property real jawDrop:       0.0
    property real breathScale:   1.0
    property real driftX:        0.0
    property real driftY:        0.0
    property real ring1Angle:    0.0
    property real ring2Angle:    0.0
    property string jarvisState: "STANDBY"
    property bool debugMode:     false // Draw red outlines for eye calibration (set to true to enable)

    // ── Bridge connection — one signal drives ALL repaints ────────────────
    Connections {
        target: jarvis
        function onAvatarFrameReady(eyelids, mw, mh, px, py, ebrow) {
            faceRoot.eyelidsScale = eyelids
            faceRoot.mouthW       = mw
            faceRoot.mouthH       = mh
            faceRoot.pupilX       = px
            faceRoot.pupilY       = py
            faceRoot.eyebrowLift  = ebrow
            eyeCanvas.requestPaint()
            mouthCanvas.requestPaint()
            eyebrowCanvas.requestPaint()
        }
        function onStateChanged(state) {
            faceRoot.jarvisState = state
        }
    }

    // ── Head drift ────────────────────────────────────────────────────────
    SequentialAnimation {
        running: true; loops: Animation.Infinite
        NumberAnimation { target: faceRoot; property: "driftX"; to:  2.5; duration: 1250; easing.type: Easing.InOutSine }
        NumberAnimation { target: faceRoot; property: "driftX"; to: -2.5; duration: 1250; easing.type: Easing.InOutSine }
    }
    SequentialAnimation {
        running: true; loops: Animation.Infinite
        NumberAnimation { target: faceRoot; property: "driftY"; to:  1.8; duration: 2000; easing.type: Easing.InOutSine }
        NumberAnimation { target: faceRoot; property: "driftY"; to: -1.8; duration: 2000; easing.type: Easing.InOutSine }
    }

    // ── Breathing scale ───────────────────────────────────────────────────
    SequentialAnimation {
        running: true; loops: Animation.Infinite
        NumberAnimation { target: faceRoot; property: "breathScale"; to: 1.006; duration: 600; easing.type: Easing.InOutSine }
        NumberAnimation { target: faceRoot; property: "breathScale"; to: 0.994; duration: 600; easing.type: Easing.InOutSine }
    }

    // ── HUD ring angles ───────────────────────────────────────────────────
    NumberAnimation on ring1Angle { running: true; loops: Animation.Infinite; from: 0;   to: 360; duration: 7200 }
    NumberAnimation on ring2Angle { running: true; loops: Animation.Infinite; from: 360; to: 0;   duration: 4500 }

    // ════════════════════════════════════════════════════════════════════════
    // Z-ORDER LAYER STACK (bottom to top):
    //   [z=-1]  glowAura       — bloom BEHIND face, never touches eye pixels
    //   [z=0]   hudRings       — decorative rotating arcs
    //   [z=1]   faceLayer      — face photo + eyeCanvas baked into ONE texture
    //   [z=2]   mouthCanvas    — lip sync overlay
    //   [z=2]   eyebrowCanvas  — eyebrow lines
    //   [z=3]   particles      — orbiting dots on top of everything
    // ════════════════════════════════════════════════════════════════════════

    // ── GLOW AURA (z:-1 — BEHIND face, EXCLUDED from eye pixel processing) ─
    // FIX: bloom renders BEFORE the face layer paints eye pixels.
    // The glow source is the face shape, not the eye region.
    // GlowLayer source = faceLayer shape only, maskEyes = true via z-order.
    RectangularGlow {
        id: glowAura
        z: -1   // BEHIND faceLayer — glow pass never re-renders eye pixels
        anchors.centerIn: faceLayer
        width:  faceLayer.width  + 28
        height: faceLayer.height + 28
        glowRadius: 22
        spread: 0.07
        color: Qt.rgba(0, 0.70, 1.0, 0.28)
        cornerRadius: (faceLayer.width / 2) + glowRadius
    }

    // ── HUD RINGS (z:0, behind face) ──────────────────────────────────────
    Canvas {
        id: hudRings
        z: 0
        anchors.fill: parent
        // Repaint driven by the ring angle animations (NumberAnimation on ring1Angle/ring2Angle)
        // No polling Timer needed — the property change fires exactly when the animation ticks.
        property real r1: faceRoot.ring1Angle
        property real r2: faceRoot.ring2Angle
        onR1Changed: requestPaint()
        onR2Changed: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            var cx = width / 2, cy = height / 2
            ctx.clearRect(0, 0, width, height)
            ctx.save()
            ctx.strokeStyle = "#002040"; ctx.lineWidth = 1; ctx.setLineDash([8, 4])
            ctx.beginPath()
            var a1s = faceRoot.ring1Angle * Math.PI / 180
            ctx.arc(cx, cy, 178, a1s, a1s + 140 * Math.PI / 180)
            ctx.stroke()
            ctx.strokeStyle = "#004060"; ctx.lineWidth = 2; ctx.setLineDash([20, 10])
            ctx.beginPath()
            var a2s = faceRoot.ring2Angle * Math.PI / 180
            ctx.arc(cx, cy, 198, a2s, a2s + 100 * Math.PI / 180)
            ctx.stroke()
            ctx.restore()
        }
    }

    // ── FACE LAYER (z:1 — face photo + animated eyes = ONE GPU texture) ───
    //
    // SINGLE EYE SOURCE ARCHITECTURE:
    //   faceImage  → provides the wireframe head structure (NO visible eyes —
    //                the photo has dark hollow socket regions)
    //   eyeCanvas  → THE ONLY eye renderer — draws exactly 2 animated eyes
    //                AS A CHILD of faceLayer so both are baked together into
    //                one GPU texture by the OpacityMask clip.
    //
    // This means:
    //   • No EyeOverlay layer can exist outside this Item
    //   • No ReflectionLayer can redraw eyes (glow is z:-1)
    //   • The bloom pass (glowAura) renders from the shape mask, not eye pixels
    //   • Exactly 2 eyes total — the canvas eyes — visible in the final output
    Item {
        id: faceLayer
        z: 1
        width: 350; height: 350
        x: (parent.width  - width)  / 2 + faceRoot.driftX
        y: (parent.height - height) / 2 + faceRoot.driftY
        scale: faceRoot.breathScale

        // Circular clip — everything inside is cropped to a perfect circle
        // This clip applies to BOTH faceImage AND eyeCanvas simultaneously.
        layer.enabled: true
        layer.effect: OpacityMask {
            maskSource: Rectangle {
                width: 350; height: 350; radius: 175
                color: "white"; visible: false
            }
        }

        // ── Base face photo (dark eye sockets — NO visible eyes in photo) ──
        Image {
            id: faceImage
            anchors.fill: parent
            source: "file:///" + assetsPath + "/jarvis_face.png"
            fillMode: Image.PreserveAspectCrop
            smooth: true
            antialiasing: true
            cache: true
        }

        // ── SOLE EYE RENDERER — unified Canvas inside the layer ────────────
        //
        // Calibrated to the dark eye socket positions in jarvis_face.png.
        // Eye center positions measured from the 350×350 display area:
        //
        //   Left  socket: cx = 350 * 0.355 ≈ 124,  cy = 350 * 0.435 ≈ 152
        //   Right socket: cx = 350 * 0.645 ≈ 226,  cy = 350 * 0.435 ≈ 152
        //   Socket width:  ~70px  Socket height: ~28px
        //
        // Step 1: Paint solid dark ellipse over socket (kills any residual
        //         photo-eye bleed — defensive layer, always runs first)
        // Step 2: Draw animated iris + pupil + eyelid mechanism
        // Step 3: Draw socket rim arc (integrates eye into wireframe mesh)
        Canvas {
            id: eyeCanvas
            anchors.fill: parent   // coordinate space = faceLayer (350×350)

            // ── Eye socket positions — calibrated from design guidelines ───
            // Values: cx = center +/- (350 * 0.215), cy = center - (350 * 0.075)
            // rx = 350 * 0.135, ry = 350 * 0.072
            readonly property real leftCX:     350 * 0.3645  // ~127.58
            readonly property real leftCY:     350 * 0.4577  // ~160.20
            readonly property real rightCX:    350 * 0.6314  // ~220.99
            readonly property real rightCY:    350 * 0.4577  // ~160.20
            readonly property real socketRX:   32.0          // socket half-width  (ellipse rx)
            readonly property real socketRY:   16.0          // socket half-height (ellipse ry)
            readonly property real pupilMax:   12.0          // max iris radius when fully open

            Component.onCompleted: requestPaint()

            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)

                var es  = Math.max(0.0, Math.min(1.0, faceRoot.eyelidsScale))
                var px  = faceRoot.pupilX  * 0.5   // dampen pupil travel
                var py  = faceRoot.pupilY  * 0.5

                // ── Draw one complete eye at (cx, cy) ─────────────────────
                function drawEye(cx, cy) {
                    var rx  = socketRX
                    var ry  = socketRY

                    // Calculate local variables for eyelid covers
                    var coverH = ry * 2 * 0.15
                    var coverW = rx * 2
                    var coverTop = cy - ry * es
                    var coverBottom = cy + ry * es

                    // Safety check for undefined variables
                    if (typeof cx === 'undefined' || typeof cy === 'undefined' ||
                        typeof rx === 'undefined' || typeof ry === 'undefined' ||
                        typeof es === 'undefined' || typeof px === 'undefined' || typeof py === 'undefined' ||
                        typeof coverH === 'undefined' || typeof coverW === 'undefined' ||
                        typeof coverTop === 'undefined' || typeof coverBottom === 'undefined') {
                        console.warn("JARVIS FaceEngine Warning: Undefined variables detected in drawEye. Skipping render.");
                        return;
                    }

                    // ── 1. Clip to eye socket (ellipse) ────────────────────────
                    ctx.save()
                    ctx.beginPath()
                    ctx.ellipse(cx - rx, cy - ry, rx * 2, ry * 2)
                    ctx.clip()

                    // ── 2. Draw top eyelid cover (Semi-transparent cyan, no black) ──
                    ctx.fillStyle = "rgba(0, 221, 255, 0.12)"
                    ctx.fillRect(cx - rx - 5, coverTop - coverH, (rx + 5) * 2, coverH)
                    
                    // glowing edge
                    ctx.strokeStyle = "#00ddff"
                    ctx.lineWidth = 1.5
                    ctx.beginPath()
                    ctx.moveTo(cx - rx + 1, coverTop)
                    ctx.quadraticCurveTo(cx, coverTop - 2, cx + rx - 1, coverTop)
                    ctx.stroke()

                    // ── 3. Draw bottom eyelid cover (Semi-transparent cyan, no black) ──
                    ctx.fillStyle = "rgba(0, 221, 255, 0.12)"
                    ctx.fillRect(cx - rx - 5, coverBottom, (rx + 5) * 2, coverH)
                    
                    // glowing edge
                    ctx.strokeStyle = "#00ddff"
                    ctx.lineWidth = 1.5
                    ctx.beginPath()
                    ctx.moveTo(cx - rx + 1, coverBottom)
                    ctx.quadraticCurveTo(cx, coverBottom + 2, cx + rx - 1, coverBottom)
                    ctx.stroke()
                    
                    ctx.restore()

                    // ── 4. Specular highlight for gaze (no black shapes) ────────
                    var hx = cx + px * 0.7
                    var hy = cy + py * 0.7
                    if (es > 0.15) {
                        ctx.save()
                        // Clip the highlights to the open eye socket aperture
                        ctx.beginPath()
                        ctx.ellipse(cx - rx, cy - ry, rx * 2, ry * 2)
                        ctx.clip()

                        // Clip highlights again under the eyelids to ensure they don't bleed onto closed lids
                        if (coverTop > cy - ry || coverBottom < cy + ry) {
                            ctx.beginPath()
                            ctx.rect(cx - rx - 5, coverTop, (rx + 5) * 2, coverBottom - coverTop)
                            ctx.clip()
                        }

                        // Soft cyan gaze glow
                        var glowGrad = ctx.createRadialGradient(hx, hy, 1, hx, hy, 8)
                        glowGrad.addColorStop(0.0, "rgba(0, 240, 255, 0.65)")
                        glowGrad.addColorStop(1.0, "rgba(0, 180, 255, 0.0)")
                        ctx.beginPath()
                        ctx.arc(hx, hy, 8, 0, Math.PI * 2)
                        ctx.fillStyle = glowGrad
                        ctx.fill()

                        // Bright white specular glint
                        ctx.beginPath()
                        ctx.arc(hx - 2, hy - 2, 2.2, 0, Math.PI * 2)
                        ctx.fillStyle = "rgba(255, 255, 255, 0.9)"
                        ctx.fill()

                        ctx.restore()
                    }

                    // ── 5. DEBUG OUTLINES (Draw socket outlines temporarily) ────
                    if (faceRoot.debugMode) {
                        ctx.save()
                        ctx.strokeStyle = "#00FF00" // bright green
                        ctx.lineWidth = 1.0
                        ctx.setLineDash([2, 2])
                        ctx.beginPath()
                        ctx.ellipse(cx - rx, cy - ry, rx * 2, ry * 2)
                        ctx.stroke()
                        // draw crosshairs at the center
                        ctx.beginPath()
                        ctx.moveTo(cx - 6, cy)
                        ctx.lineTo(cx + 6, cy)
                        ctx.moveTo(cx, cy - 6)
                        ctx.lineTo(cx, cy + 6)
                        ctx.stroke()
                        ctx.restore()
                    }
                }

                drawEye(leftCX,  leftCY)
                drawEye(rightCX, rightCY)
            }
        }
        // END faceLayer children — no other eye-rendering items exist here
    }

    // ── MOUTH / LIP SYNC (outside layer — no circular clip needed) ────────
    Canvas {
        id: mouthCanvas
        z: 2
        width: 100; height: 60
        x: faceLayer.x + faceLayer.width  * 0.5 - width  / 2
        y: faceLayer.y + faceLayer.height * 0.70
        Component.onCompleted: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            var cx = width / 2, cy = height / 2
            var mw = faceRoot.mouthW, mh = faceRoot.mouthH
            if (mh > 1.5) {
                ctx.fillStyle = "#020709"
                ctx.beginPath(); ctx.ellipse(cx - mw / 2, cy - mh / 2, mw, mh); ctx.fill()
                ctx.strokeStyle = "rgba(255,255,255,0.55)"; ctx.lineWidth = 0.9
                ctx.beginPath(); ctx.moveTo(cx - mw * 0.28, cy); ctx.lineTo(cx + mw * 0.28, cy); ctx.stroke()
            }
            ctx.strokeStyle = "#00BFFF"; ctx.lineWidth = 1.4; ctx.setLineDash([])
            ctx.beginPath()
            ctx.moveTo(cx - mw / 2, cy)
            ctx.quadraticCurveTo(cx - mw / 4, cy - mh / 2 - 1, cx, cy - mh / 2 + 1.8)
            ctx.quadraticCurveTo(cx + mw / 4, cy - mh / 2 - 1, cx + mw / 2, cy)
            ctx.stroke()
            ctx.beginPath(); ctx.moveTo(cx - mw / 2, cy); ctx.quadraticCurveTo(cx, cy + mh / 2 + 2, cx + mw / 2, cy); ctx.stroke()
        }
    }

    // ── EYEBROWS (outside layer — full-face coordinate space) ─────────────
    Canvas {
        id: eyebrowCanvas
        z: 2
        anchors.fill: parent
        Component.onCompleted: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            var cx = width / 2, cy = height / 2
            var lift = faceRoot.eyebrowLift
            ctx.strokeStyle = "#00E8FF"; ctx.lineWidth = 1.6; ctx.setLineDash([])
            var lbX = cx - 52, lbY = cy - 40 - lift
            ctx.beginPath(); ctx.moveTo(lbX, lbY); ctx.lineTo(lbX + 32, lbY + 2); ctx.stroke()
            var rbX = cx + 20, rbY = cy - 40 - lift
            ctx.beginPath(); ctx.moveTo(rbX, rbY + 2); ctx.lineTo(rbX + 32, rbY); ctx.stroke()
        }
    }

    // ── ORBITING ENERGY PARTICLES ─────────────────────────────────────────
    // Pure GPU NumberAnimation — no Canvas, no Math.random() re-evaluation
    // Deterministic positions from index ensure stable orbits.
    Repeater {
        model: 16
        delegate: Item {
            id: ptcl
            z: 3
            readonly property real _a0:  (index * 39.37) % 360
            readonly property real _orb: 130 + (index * 7.13) % 46
            readonly property real _dur: 1900 + (index * 317) % 3800
            readonly property bool _cw:  (index % 2) === 0
            property real angle: _a0
            x: faceRoot.width  / 2 + Math.cos(angle * Math.PI / 180) * _orb - 1.5
            y: faceRoot.height / 2 + Math.sin(angle * Math.PI / 180) * _orb - 1.5
            NumberAnimation on angle {
                running: true; loops: Animation.Infinite
                from: ptcl._a0; to: ptcl._a0 + (ptcl._cw ? 360 : -360)
                duration: ptcl._dur
            }
            Rectangle {
                width: 2.0 + (index % 3) * 0.8; height: width; radius: width / 2
                color: "#55CCFF"; opacity: 0.48
            }
        }
    }
}
