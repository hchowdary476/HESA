"""Smoke helpers for validating the desktop UI without starting Jarvis runtime."""

from __future__ import annotations


def run_ui_smoke() -> dict:
    """Instantiate the PySide6 application, load QML, and close it immediately."""
    import os
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtCore import QUrl
    from JARVIS.gui.qml_bridge import JarvisBridge
    from JARVIS.gui.ui_avatar import JarvisAvatarState

    app = QApplication.instance() or QApplication(sys.argv)
    
    avatar = JarvisAvatarState()
    bridge = JarvisBridge()
    bridge.attach_avatar(avatar)
    
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("jarvis", bridge)
    
    assets_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "assets")
    )
    engine.rootContext().setContextProperty("assetsPath", assets_path)
    
    qml_main = os.path.join(os.path.dirname(__file__), "qml", "main.qml")
    engine.load(QUrl.fromLocalFile(qml_main))
    
    if not engine.rootObjects():
        return {
            "status": "error",
            "title": "",
            "geometry": "",
            "widgets": 0,
        }
        
    root_obj = engine.rootObjects()[0]
    title = root_obj.property("title")
    width = root_obj.property("width")
    height = root_obj.property("height")
    
    # Clean up
    avatar.stop()
    bridge.stop()
    
    return {
        "status": "ok",
        "title": title,
        "geometry": f"{width}x{height}",
        "widgets": len(engine.rootObjects()),
    }


def main() -> int:
    result = run_ui_smoke()
    print(f"UI smoke: {result['status']}")
    print(f"Window title: {result['title']}")
    print(f"Top-level widgets: {result['widgets']}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
