// JarvisFont.qml — Global font singleton for the JARVIS interface
// Loads Orbitron once; all QML files reference JarvisFont.orbitron
//
// Placed in the qml/ folder.  Font files are in assets/fonts/ relative
// to the project root.  The Python side sets assetsPath as a context
// property, so we build the URL at runtime.
//
// Usage anywhere in QML:
//   font.family: JarvisFont.orbitron

pragma Singleton
import QtQuick 2.15

Item {
    id: fontSingleton

    readonly property string _base: {
        var path = (typeof assetsPath !== "undefined" && assetsPath !== "")
                   ? assetsPath
                   : Qt.resolvedUrl("../../../assets").toString()
        if (path.indexOf("file://") === 0 || path.indexOf("qrc:/") === 0) {
            return path
        }
        var cleanPath = path.replace(/\\/g, "/")
        if (cleanPath.indexOf(":") !== -1) {
            if (cleanPath.charAt(0) !== "/") {
                cleanPath = "/" + cleanPath
            }
            return "file://" + cleanPath
        }
        return "file://" + cleanPath
    }

    // ── Regular weight (400) ──────────────────────────────────────────────
    FontLoader {
        id: orbitronRegular
        // File URL works with QUrl.fromLocalFile scheme (no qrc needed)
        source: fontSingleton._base + "/fonts/Orbitron-Regular.ttf"
        onStatusChanged: {
            if (status === FontLoader.Error)
                console.warn("[JarvisFont] Orbitron Regular NOT found at: " + source + " — falling back to Segoe UI")
            else if (status === FontLoader.Ready)
                console.log("[JarvisFont] Orbitron loaded OK → family='" + name + "'")
        }
    }

    // ── Bold weight (700) ─────────────────────────────────────────────────
    FontLoader {
        id: orbitronBold
        source: fontSingleton._base + "/fonts/Orbitron-Bold.ttf"
        onStatusChanged: {
            if (status === FontLoader.Error)
                console.warn("[JarvisFont] Orbitron Bold NOT found — falling back to Segoe UI")
        }
    }

    // ── Public properties ─────────────────────────────────────────────────

    /// Orbitron family string (safe — falls back to Segoe UI if not loaded)
    readonly property string orbitron: {
        if (orbitronRegular.status === FontLoader.Ready)
            return orbitronRegular.name
        return "Segoe UI"
    }

    /// Monospace alias — always available on Windows
    readonly property string mono: "Consolas"
}
