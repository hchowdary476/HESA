"""Screenshot regression checks for the JARVIS desktop QML cockpit."""

from __future__ import annotations

import sys
import os
import time
from pathlib import Path
from PIL import Image
from PySide6.QtQuick import QQuickWindow

# High-DPI + GPU setup to match main_window.py
os.environ.setdefault("QT_QUICK_BACKEND", "rhi")
os.environ.setdefault("QSG_RHI_BACKEND", "d3d11")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

PAGES_TO_CAPTURE = ("dashboard", "system", "cybersecurity", "diagnostics")
MIN_CYAN_PIXELS = 900
MIN_BRIGHT_PIXELS = 1800

def validate_metrics(metrics: dict) -> tuple[bool, list[str]]:
    """Validate screenshot metrics against stable HUD health thresholds."""
    failures = []
    if metrics["width"] < 1200 or metrics["height"] < 700:
        failures.append("screenshot resolution is too small")
    if metrics["cyan_pixels"] < MIN_CYAN_PIXELS:
        failures.append("cyan HUD signal is too weak")
    if metrics["bright_pixels"] < MIN_BRIGHT_PIXELS:
        failures.append("visible UI content is too sparse")
    if metrics["dark_pixels"] < metrics["bright_pixels"]:
        failures.append("dark cockpit background is not dominant")
    return not failures, failures

def analyze_image(path: str | Path) -> dict:
    """Return visual health metrics for a captured cockpit screenshot."""
    image = Image.open(path).convert("RGB")
    pixel_access = image.load()
    pixels = [pixel_access[x, y] for y in range(image.height) for x in range(image.width)]
    cyan_pixels = sum(1 for r, g, b in pixels if g > 130 and b > 150 and r < 80)
    bright_pixels = sum(1 for r, g, b in pixels if r + g + b > 180)
    dark_pixels = sum(1 for r, g, b in pixels if r + g + b < 45)
    return {
        "path": str(path),
        "width": image.width,
        "height": image.height,
        "cyan_pixels": cyan_pixels,
        "bright_pixels": bright_pixels,
        "dark_pixels": dark_pixels,
    }

def run_screenshot_regression(output_dir: str | Path = "exports") -> dict:
    """Capture key QML pages and verify they are nonblank HUD screens."""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtCore import QUrl, QTimer, QCoreApplication
    from JARVIS.gui.qml_bridge import JarvisBridge
    from JARVIS.gui.ui_avatar import JarvisAvatarState

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
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
        avatar.stop()
        bridge.stop()
        return {"status": "failed", "results": []}
        
    root_obj = engine.rootObjects()[0]
    results = []
    
    # Geometry setup matching HUD standard specs
    root_obj.setProperty("width", 1600)
    root_obj.setProperty("height", 900)
    root_obj.setProperty("visible", True)

    pages = list(PAGES_TO_CAPTURE)
    
    def capture_next():
        if not pages:
            avatar.stop()
            bridge.stop()
            # Only quit the event loop if this module IS the entry point.
            # When imported inside jarvis.py we must NOT terminate the GUI's
            # event loop — only quit when running standalone for regression tests.
            import __main__ as _main_module
            _is_standalone = getattr(_main_module, "__file__", "").endswith(
                "ui_screenshot_regression.py"
            )
            if _is_standalone:
                QCoreApplication.quit()
            return
            
        page = pages.pop(0)
        root_obj.setProperty("activePage", page)
        
        # Take screenshot after allowing rendering cycle to complete
        def grab_screenshot():
            qimg = root_obj.grabWindow()
            filename = output_dir / f"ui-regression-{page}.png"
            qimg.save(str(filename))
            
            metrics = analyze_image(filename)
            ok, failures = validate_metrics(metrics)
            results.append({"page": page, "ok": ok, "failures": failures, **metrics})
            
            # Queue next page capture
            QTimer.singleShot(200, capture_next)
            
        QTimer.singleShot(200, grab_screenshot)
        
    # Start sequence after initial initialization delay
    QTimer.singleShot(500, capture_next)
    
    app.exec()
    
    return {
        "status": "ok" if all(result["ok"] for result in results) else "failed",
        "results": results,
    }

def main() -> int:
    report = run_screenshot_regression()
    print(f"UI screenshot regression: {report['status']}")
    for result in report["results"]:
        print(
            f"{result['page']}: {result['width']}x{result['height']} "
            f"cyan={result['cyan_pixels']} bright={result['bright_pixels']} "
            f"failures={','.join(result['failures']) or 'none'}"
        )
    return 0 if report["status"] == "ok" else 1

if __name__ == "__main__":
    raise SystemExit(main())
